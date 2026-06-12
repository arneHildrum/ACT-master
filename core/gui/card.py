# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import abc

from act.core.utils.logger import log
from jinja2 import Template
from plotly.graph_objs._figure import Figure


class Card:
    """
    A class that abstracts a Bootstrap Card UI component.

    This class provides functionality to create and manage card-based UI components
    that can display various types of content including HTML and Plotly figures.
    Cards are the basic building blocks of the ACT dashboard interface.

    Cards can be constructed with a title and either HTML content or a Plotly Figure.
    They can be serialized into either a Dash object for interactive dashboards,
    or a static HTML string via templates for static reports.
    """

    t_card_template = Template(
        """<div class="card" style="width: 100%;" id={{ id }}>
                <div style="background-color: gray" class="card-header d-flex align-items-center">
                        <h4 class="card-title text-white">{{ title }}</h4>
                </div>
                <div class="card-body">
                    {{ content | safe }}
                </div>
            </div>
        """,
        autoescape=True,
    )

    HAS_TABLE = False
    HAS_PLOT = False

    def __init__(self, id, title, content=None) -> None:
        """
        Initialize a Card object with an ID, title, and content.

        Args:
            id (str): Unique identifier for the card. Must start with an alphabetic character.
            title (str): Title to display in the card header.
            content (str, Figure, optional): Content to display in the card body.
                Can be HTML string or a Plotly Figure object. If None, an error will be raised.

        Raises:
            ValueError: If content is neither a Plotly Figure nor an HTML string.
            SystemExit: If no content is provided or if ID doesn't start with an alphabetic character.
        """

        if content is None or content == "":
            log.critical(
                f"No content provided for card {title}. This will generate a blank card and should be fixed."
            )
            exit(-1)

        if not id[0].isalpha():
            log.critical(
                f"Card IDs must start with a alphabetic character and not a number or symbol otherwise it will yield an invalid target for javascript selectors. Got {id}."
            )
            exit(-1)

        self.id = id
        self.title = title
        self.content = content

        if isinstance(self.content, Figure):
            content.update_layout(autosize=True, width=None, height=None)
            self.html_content = content.to_html()
        elif isinstance(self.content, str):
            self.html_content = content
        else:
            raise ValueError(
                "Generated content to card was neither a Ploty Figure or html string."
            )

    def _init_table_dict(self, tables: list) -> None:
        """Initialize a dictionary of tables indexed by their class names.

        This method creates a dictionary that maps table class names to table objects,
        making it easy to access specific tables by their type. The dictionary is stored
        as the 'table' attribute of the card.

        Args:
            tables (list): A list of table objects to be indexed.

        Side effects:
            Sets the 'table' attribute of the card to a dictionary mapping table class names
            to table objects.
        """
        self.table = {}
        for t in tables:
            self.table[type(t).__name__] = t

    def _init_plot_dict(self, plots: list) -> None:
        """Initialize a dictionary of plots indexed by their class names.

        This method creates a dictionary that maps plot class names to plot objects,
        making it easy to access specific plots by their type. The dictionary is stored
        as the 'plot' attribute of the card.

        Args:
            plots (list): A list of plot objects to be indexed.

        Side effects:
            Sets the 'plot' attribute of the card to a dictionary mapping plot class names
            to plot objects.
        """
        self.plot = {}
        for p in plots:
            self.plot[type(p).__name__] = p

    def to_html(self) -> str:
        """
        Serialize the card into HTML using the built-in template.

        Renders the card's title and content into an HTML string using the
        card template defined in the class.

        Returns:
            str: HTML representation of the card.
        """
        card = self.t_card_template.render(
            {"title": self.title, "content": self.html_content, "id": self.id}
        )

        return card

    def make_hlink(self, card, text):
        """
        Create a hyperlink that activates another card when clicked.

        Args:
            card (str): ID of the target card to activate.
            text (str): Display text for the hyperlink.

        Returns:
            str: HTML anchor tag that will activate the specified card when clicked.
        """
        return f'<a href="#stub" onclick="activateCard(event, \'{card}\')"; return true;">{text}</a>'

    @abc.abstractmethod
    def generate_content(self):
        """Generate HTML content for the card body.

        This abstract method must be implemented by all Card subclasses to provide
        the specific content to be displayed in the card body. The implementation
        should generate and return HTML that will be rendered within the card's
        content area.

        The content can include any valid HTML, such as text, tables, plots,
        or interactive elements, formatted according to the specific needs of
        the card type.

        Returns:
            str: HTML content to render in the body of this card.

        Raises:
            NotImplementedError: If a subclass does not implement this method.
        """
        raise NotImplementedError("Card content generation not defined.")
