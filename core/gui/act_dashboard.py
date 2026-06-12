# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import importlib.resources
import os
import shutil
import tempfile

import htmlark
from act.core.gui.cards.bill_of_materials_card import BillOfMaterialsCard
from act.core.gui.cards.carbon_card import CarbonCard
from act.core.gui.cards.cost_card import CostCard
from act.core.gui.cards.scalability_card import ScalabilityCard
from act.core.gui.cards.sim_info_card import SimInfoCard
from act.core.gui.cards.supply_chain_card import SupplyChainCard
from act.core.gui.tabs import Tabs
from act.core.utils.logger import log
from jinja2 import Template
from requests import RequestException


class ACTDashboard:
    """
    A dashboard for displaying Architecture Carbon Tool (ACT) results.

    This class handles the creation and rendering of a dashboard with various cards
    displaying different aspects of the ACT analysis results. It can generate both
    standard HTML files and self-contained packed HTML files with all assets embedded.

    The dashboard uses a tabbed interface to organize different cards, each showing
    specific information about the carbon analysis.
    """

    def __init__(
        self,
        act,
        html_file: str = "act.html",
        out_dir: str = None,
        export_plot=False,
        init_tab=None,
        test=False,
        description="Default System Name",
        dashboard_title="Architecture Carbon Tool Results",
    ):
        """
        Initialize the ACT Dashboard.

        Args:
            act: The ACT analysis object containing results data
            html_file (str): Filename for the output HTML file
            out_dir (str, optional): Directory to output the HTML files. If None, a temporary directory is created
            export_plot (bool): Whether to export plots as separate files
            init_tab: The initial tab to display when the dashboard is loaded
            test (bool): Whether the dashboard is being generated for testing purposes
            description (str): Description of the system being analyzed
            dashboard_title (str): Title to display on the dashboard

        The constructor sets up the dashboard structure and copies required template files
        to the output directory.
        """
        self.html_file = html_file
        self.export_plot = export_plot
        self.cards = []
        self.init_tab = init_tab
        self.test = test
        self.description = description
        self.dashboard_title = dashboard_title
        self.uri = None
        self.act = act

        if out_dir is not None:
            self.out_dir = out_dir
        else:
            temp_out = tempfile.TemporaryDirectory(prefix="act_ui_").name
            self.out_dir = temp_out
        self.packed_html_file = None

        # copy out the html template to the output directory
        self.copy_templates(self.out_dir)

    def generate_dashboard(self, extra_cards=None):
        """
        Generate the complete dashboard with all standard cards.

        Creates and adds the standard set of cards to the dashboard:
        - Carbon card
        - Supply chain card
        - Bill of materials card
        - Analysis info card

        Then renders the dashboard to HTML.
        """
        carbon_card = CarbonCard(act=self.act)
        self.add_card(carbon_card)

        cost_card = CostCard(act=self.act)
        self.add_card(cost_card)

        supply_chain_card = SupplyChainCard(act=self.act)
        self.add_card(supply_chain_card)

        bill_of_materials_card = BillOfMaterialsCard(act=self.act)
        self.add_card(bill_of_materials_card)

        scalability_card = ScalabilityCard(act=self.act)
        self.add_card(scalability_card)

        if extra_cards is not None:
            for card in extra_cards:
                self.add_card(card)

        sim_info_card = SimInfoCard(act=self.act)
        self.add_card(sim_info_card)

        self.render()

    def copy_templates(self, html_path="html"):
        """
        Copy HTML template files to the specified output directory.

        This method copies all HTML template files from the package's assets.html
        directory to the specified output directory. These templates are necessary
        for rendering the dashboard with proper styling and layout.

        Args:
            html_path (str, optional): Path where HTML template files should be copied.
                Defaults to "html" in the current directory.

        The function ensures the destination directory exists, creating it if necessary,
        and preserves the original filenames during copying.

        Note:
            This method is called during dashboard initialization to ensure all required
            template files are available in the output directory before rendering
            the dashboard.
        """
        template_files = importlib.resources.files(__package__ + ".assets.html")
        html_path = os.path.abspath(html_path) + "/"
        if not os.path.exists(html_path):
            os.makedirs(html_path, exist_ok=True)

        for template_file in template_files.iterdir():
            fname = os.path.basename(template_file)
            shutil.copyfile(template_file, os.path.join(html_path, fname))

    def render(self):
        """
        Converts the dashboard assets to HTML.

        Generates the HTML for all cards, creates the tabbed interface,
        and produces both a standard HTML file and a self-contained packed
        HTML file with all assets embedded (unless in test mode).
        The packed HTML file contains all resources embedded within it for easy sharing.

        Raises:
            AssertionError: If no cards have been added to the dashboard
        """

        assert len(self.cards) > 0, (
            "No dashboard cards were added. Dashboard must have at least 1 card added to render properly."
        )

        # create the tab html content
        content = Tabs(
            id="tabs",
            title=self.dashboard_title,
            content=self.cards,
        )

        # convert the contents to html with initial tab specification
        plot_data = [content.to_html(initial_tab=self.init_tab)]

        index_file = os.path.join(self.out_dir, "index.html")

        self.generate_html("".join(plot_data), index_file=index_file)

        # Render the packed static html result
        packed_html = ""
        if not self.test:
            try:
                packed_html = htmlark.convert_page(
                    index_file,
                    ignore_errors=True,
                )
            except (ValueError, OSError, NameError, RequestException) as e:
                log.error(e)
                log.error("Could not create a single file HTML dashboard.")

        # Write out the packed HTML
        self.packed_html_file = os.path.join(self.out_dir, self.html_file)
        with open(self.packed_html_file, "w") as fd:
            fd.write(packed_html)

    def get_html_import_path(self):
        """
        Return the package path for importing HTML assets.

        Returns:
            str: The fully qualified package path where HTML template assets are stored.
                This path is used by importlib.resources to locate and load HTML templates
                needed for dashboard rendering.

        This method provides a consistent way to access the HTML template assets
        regardless of where the package is installed in the Python environment.
        """
        return __package__ + ".assets.html"

    def generate_html(self, payload, index_file="index.html"):
        """
        Generate HTML content for the dashboard using templates.

        This method loads the HTML template from the package resources, applies the
        provided payload content using Jinja2 templating, and writes the resulting
        HTML to the specified output file.

        Args:
            payload (str): The HTML content to insert into the template, typically
                containing the tabbed interface with all dashboard cards.
            index_file (str, optional): Path where the generated HTML file should be saved.
                Defaults to "index.html" in the current directory.
        """
        # load the html template
        import_path = self.get_html_import_path()
        with importlib.resources.path(import_path, "index.html") as resource_path:
            with open(resource_path) as handle:
                html_template = handle.read()

        # jinja the template with the results
        jinja_template = Template(html_template)
        dashboard_html = jinja_template.render(
            {"tab_payload": payload, "page_title": "Architecture Carbon Tool Results"}
        )

        with open(index_file, "w") as handle:
            handle.write(dashboard_html)

    def add_card(self, card):
        """
        Add a single card to the dashboard.

        Args:
            card: The card object to add to the dashboard
        """
        self.cards.append(card)

    def add_cards(self, cards):
        """
        Add multiple cards to the dashboard at once.

        Args:
            cards: A list of card objects to add to the dashboard
        """
        self.cards.extend(cards)

    def get_card(self, cid=None, title=None):
        """
        Find and return a dashboard card matching the specified criteria.

        Args:
            cid (str, optional): The ID of the card to find. If None, this criterion is ignored.
            title (str, optional): The title of the card to find. If None, this criterion is ignored.

        Returns:
            Card: The first card that matches all specified criteria, or None if no match is found.
                If both cid and title are None, the first card will be returned.
        """
        for card in self.cards:
            if (card.id == cid or cid is None) and (
                card.title == title or title is None
            ):
                return card
        return None

    def get_card_by_type(self, ctype):
        """
        Find and return the first dashboard card matching the specified type.

        Args:
            ctype: The class type to match against cards in the dashboard

        Returns:
            The first card that matches the specified type, or None if no match is found
        """
        for c in self.cards:
            if isinstance(c, ctype):
                return c
        return None
