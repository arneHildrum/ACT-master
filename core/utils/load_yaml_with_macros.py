# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
import re

import pint
import yaml
from act.core.common import MACROS
from act.core.utils.logger import log

MACRO_DELIMITER = "="

# PROHIBITED_OPERATORS: The set of operators that are forbidden in expressions
PROHIBITED_OPERATORS = {"//", "+", "*", "-", "/", "%", "**"}


def parse_macros(macro_clauses: str):
    cl_macros = {}
    for clause in macro_clauses:
        tokens = clause.split(MACRO_DELIMITER)
        assert len(tokens) == 2, (
            f"Macro tokens must take format var=text. Got {clause}."
        )
        var, text = tokens[0], tokens[1]
        cl_macros[var] = text
    return cl_macros


def load_yaml_with_macros(
    target_file: str, cl_macros: dict = None, out_dir: str = None, delete_macros=False
):  # noqa: C901
    """Load the yaml data from the target file and apply macros

    Args:
        target_file(str): The target file to
        cl_macros(dict): Command line macros to apply to this file
        out_dir(str): The location to write out the preprocessed yaml file

    Returns: A dict of the yaml data with macro preprocessed and substituted

    """

    # default to empty cl macros if none are provided
    if cl_macros is None:
        cl_macros = {}

    # if the cl macro is defined but it's empty, explicitly force empty string
    for macro, value in cl_macros.items():
        if value is None:
            cl_macros[macro] = '""'

    with open(target_file) as handle:
        yaml_str = handle.read()
        # This YAML may contain key duplicates due to macros that haven't been applied yet (e.g. #if/#else)
        yaml_data = yaml.load(yaml_str, Loader=yaml.FullLoader)

        # check to make sure there's something actually in the loaded yaml file
        if yaml_data is None or len(yaml_data) == 0:
            log.error(
                f"Error: The loaded yaml file {yaml_str} is empty and therefore not valid. Please fix this before continuing."
            )
            exit(-1)

        # apply macros before parsing the yaml data
        macros = yaml_data[MACROS] if MACROS in yaml_data else {}
        for macro, value in macros.items():
            if value is None:
                macros[macro] = '""'
        macros = {k: str(v) for k, v in macros.items()}  # cast all value to string
        macros.update(cl_macros)  # override with cl_macros if there is aliasing
        rewritten_yaml = apply_macros(target=yaml_str, macros=macros)

        # check the file for any macros which did not get bound properly and make them blank as per standard cpp preprocessing behavior
        unbound_macros = re.findall(r"\$\(.*?\)", rewritten_yaml)

        if len(unbound_macros) > 0:
            for unbound in unbound_macros:
                log.warn(
                    f"In {target_file}, macro {unbound} was not bound. Using a blank default value. If this is not expected, please fix these by defining the macro value."
                )
                rewritten_yaml = rewritten_yaml.replace(unbound, '""')

        # always preprocess with if else def
        preprocessed_yaml = apply_ifdef(rewritten_yaml, target_file)

        # reload the yaml data with the macro overrides
        try:
            yaml_data = yaml.load(
                preprocessed_yaml, Loader=yaml.FullLoader
            )  # ensure no duplicate keys
            yaml_data[MACROS] = (
                macros  # override with updates so that the preprocessed file reflects the updated macros
            )
        except ValueError as e:
            log.error(f"File with dupe key: {target_file}\n\texception: {e}")
            exit(-1)

    # write out the preprocessed files to inspection if the out directory is not None
    if out_dir is not None and out_dir != "":
        preprocessed_file = os.path.basename(target_file)
        with open(out_dir + "/" + preprocessed_file, "w") as handle:
            yaml.dump(yaml_data, handle)

    if delete_macros:
        del yaml_data[MACROS]

    return yaml_data


def apply_macros(target: str, macros: dict):
    """Applies macros to the target string and returns the target string with string substitutions.

    Args:
        target_file(str): The target file to copy out and replace macros for
        macros(dict): The top level macros that are passed from command line

    Returns: The rewritten file name of the preprocessed files

    """

    # apply all macro substitutions
    for var, text in macros.items():
        var_target = "$(" + str(var) + ")"
        target = target.replace(var_target, str(text))

    return target


# Helper function to check for forbidden operators
def check_forbidden_operators(content_str: str, target_file: str, line_num: int):
    """
    Checks for the presence of forbidden operators in a given string and logs an error if any are found.

    Args:
        content_str (str): The string content to check for forbidden operators.
        target_file (str): The name of the file being processed, used for logging purposes.
        line_num (int): The line number in the file where the content is located, used for logging purposes.
    """
    for op in PROHIBITED_OPERATORS:
        if op in content_str:
            # Log error to stderr and exit
            log.error(
                f"Error: Forbidden operator '{op}' found in expression in {target_file} at line {line_num}: '{content_str}'"
            )
            exit(-1)  # Exit script with status -1


# Helper function to safely evaluate the expression
def safe_eval(expression_str: str, target_file: str, line_num: int):
    """
    Evaluates a string expression with pint units using eval().
    Expression can also include pint units
    """
    check_forbidden_operators(
        expression_str, target_file, line_num
    )  # Exits if forbidden

    # Find and replace all units
    pattern = re.compile(r"(\d+(?:\.\d+)?)\s+(\w+)")

    # Replacement function: uses pint.Quantity constructor
    def replacer(match_obj):
        number = match_obj.group(1)
        unit = match_obj.group(2)
        return f"Quantity({number}, '{unit}')"

    preprocessed_string = pattern.sub(replacer, expression_str)

    # Prepare context for eval()
    eval_globals = {"__builtins__": {}}
    eval_locals = {
        "Quantity": pint.Quantity,
        "True": True,
        "False": False,
        "None": None,
    }

    # Evaluate the preprocessed string
    try:
        result = eval(preprocessed_string, eval_globals, eval_locals)
        return bool(result)
    except ValueError as e:
        log.error(
            f"Cannot eval expression in {target_file} at line {line_num}: '{expression_str}'. Error: {e}."
        )
        exit(-1)  # Exit script with status -1


def apply_ifdef(input_text: str, target_file: str) -> str:  # noqa: C901
    """
    NOTE(amrsuleiman): This function is generated mostly by AI

    Preprocesses text (like YAML) with C-style directives. Directive matching
    is CASE-SENSITIVE and requires NO SPACE between '#' and the directive
    (e.g., '#if' is valid, '# if' is ignored). Uses word boundaries (\b).
    Treats #ifdef IDENTICAL to #if, and #ifndef as the logical negation of #if.
    Uses Python's eval() for lowercase #if/#ifdef/#ifndef/#elif conditions WITHOUT
    external context, and errors/exits if specific arithmetic operators
    (+, *, -, /, %, **, //) are found.

    Evaluation Rules:
    - lowercase #if/#ifdef/#ifndef/#elif EXPRESSION (NO space after #): Uses full
      evaluation pipeline (quote strip, operator check(exit), ast check, eval)
      common logic. #ifndef negates result.
    - Other lines (including '# if', '#IF', comments): Treated as regular text,
      output only if the current conditional block is active.

    Args:
        input_text: The string containing the text to preprocess.

    Returns:
        The preprocessed text as a string (if no forbidden operators cause exit).

    Raises:
        ValueError: For syntax errors like mismatched directives (but not for operators).
    """

    # Regex to find directives and their arguments
    directive_re = re.compile(
        r"^\s*#(ifdef\b|ifndef\b|if\b|elif\b|else\b|endif\b)\s*(.*)"
    )

    lines = input_text.splitlines()
    output_lines = []

    # State stack: Each element is a tuple: (is_block_currently_active, was_if_or_elif_true_in_block)
    stack = [(True, False)]  # Base level: always active, no condition met yet

    for i, line in enumerate(lines):
        match = directive_re.match(line)

        if match:
            directive = match.group(1).lower()
            expression_str_raw = match.group(2).strip()
            line_num = i + 1

            # Helper function to get the effective string content
            def get_effective_content(raw_str: str) -> str:
                content = raw_str
                if len(content) >= 2:
                    if content.startswith('"') and content.endswith('"'):
                        content = content[1:-1]
                    elif content.startswith("'") and content.endswith("'"):
                        content = content[1:-1]
                return content

            parent_allows_activity, _ = stack[-1]

            # Directive Processing Logic

            if directive in ("if", "ifdef", "ifndef"):
                # Consolidate evaluation logic for if/ifdef/ifndef's base condition
                base_result = False  # Default to False
                effective_content = get_effective_content(expression_str_raw)
                is_content_empty = not bool(effective_content)

                if is_content_empty:
                    # Empty content means False for the base condition
                    if directive in (
                        "if",
                        "ifdef",
                    ):  # Only warn if empty directly means False
                        log.warning(
                            f"Warning: #ifdef has empty effective content in {target_file} at line {line_num} ('{expression_str_raw}')"
                        )
                    base_result = False
                else:
                    # Apply full evaluation pipeline
                    base_result = safe_eval(effective_content, target_file, line_num)
                    # End evaluation pipeline

                # Final result calculation (negate for #ifndef)
                final_result = False
                if directive == "ifndef":
                    final_result = not base_result
                else:  # for #if and #ifdef
                    final_result = base_result

                # Push state
                is_active = parent_allows_activity and final_result
                # For the stack, store the state based on the *final* result,
                # but the 'condition_already_met' flag should reflect if *any* if/elif
                # in the block evaluated to true based on its *own* logic (before negation for ifndef).
                # However, since if/ifdef/ifndef start a new block, the prior 'condition_met'
                # doesn't matter for this push. The pushed 'condition_met' should be based
                # on the final_result to correctly control subsequent elif/else.
                stack.append((is_active, final_result))

            elif directive == "elif":
                # ELIF Logic (remains mostly the same, uses eval)
                if len(stack) <= 1:
                    raise ValueError(
                        f"Syntax error: #elif without matching #if/#ifdef/#ifndef in {target_file} at line {line_num}"
                    )

                _, condition_already_met = stack[-1]
                parent_allows_activity, _ = stack[-2]

                result = False  # Default for elif
                if parent_allows_activity and not condition_already_met:
                    # Evaluate elif condition only if allowed and block condition not yet met
                    effective_content = get_effective_content(expression_str_raw)
                    is_content_empty = not bool(effective_content)

                    if is_content_empty:
                        log.warning(
                            f"Warning: #elif has empty effective content in {target_file} at line {line_num} ('{expression_str_raw}')"
                        )
                        result = False
                    else:
                        result = safe_eval(effective_content, target_file, line_num)
                # else: if parent not active or condition met, result remains False

                # Update elif state
                is_active = parent_allows_activity and result
                # Mark condition as met if it wasn't already and the current result is True
                new_condition_met = condition_already_met or result
                stack[-1] = (is_active, new_condition_met)

            elif directive == "else":
                # ELSE Logic (remains the same)
                if len(stack) <= 1:
                    raise ValueError(
                        f"Syntax error: #else without matching #if/#ifdef/#ifndef in {target_file} at line {line_num}"
                    )
                if expression_str_raw:
                    log.warning(
                        f"Warning: Expression ignored for #else directive in {target_file} at line {line_num}: '{expression_str_raw}'"
                    )

                _, condition_already_met = stack[-1]
                parent_allows_activity, _ = stack[-2]

                # Activate else only if parent allows and condition wasn't already met
                is_active = parent_allows_activity and not condition_already_met
                # Update state: block is now active (if conditions met), condition is now definitely met
                stack[-1] = (is_active, True)

            elif directive == "endif":
                # ENDIF Logic (remains the same)
                if len(stack) <= 1:
                    raise ValueError(
                        f"Syntax error: Unmatched #endif in {target_file} at line {line_num}"
                    )
                stack.pop()

        else:  # Regular line
            current_block_active, _ = stack[-1]
            if current_block_active:
                output_lines.append(line)

    if len(stack) > 1:
        raise ValueError(
            f"Syntax error: Unterminated #if/#ifdef/#ifndef block(s) at end of input in {target_file}"
        )

    return "\n".join(output_lines)
