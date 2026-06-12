# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from jinja2 import Template


class Tabs:
    """
    This class abstracts a Bootstrap Tab object for organizing dashboard content.

    The Tabs class provides a way to organize multiple Card objects into a tabbed
    interface using Bootstrap's tab component. It handles the generation of the
    necessary HTML structure for tabs and their content areas.

    Tabs can be constructed with a unique ID, title, and a list of Card objects as content.
    The class renders the tabs and their content into HTML that can be included in the
    dashboard. It manages the active/inactive state of tabs and ensures proper linking
    between tab buttons and their corresponding content panes.
    """

    t_tab_template = Template(
        """
        <button class="nav-link {{ class }}" id="nav-{{href}}" data-bs-toggle="tab" data-bs-target="#{{href}}" type="button" role="tab"> {{ tab_name }}</button>
        """
    )

    t_tab_content_template = Template(
        """
        <div class="tab-pane fade {{ class }}" id="{{ id }}">


        {{ content }}
    </div>
    """
    )

    t_top_template = Template(
        """

      <nav>
        <div class="nav nav-tabs" id="nav-tab" role="tablist">
        {{ tabs }}
        </div>
      </nav>


      <div class="tab-content" id="nav-tabContent">
        {{ content }}
      </div>
    """
    )

    def __init__(self, id, title, content) -> None:
        """
        Initialize a Tabs object with an ID, title, and content.

        Args:
            id (str): Unique identifier for the tabs component.
            title (str): Title to display for the tabs component.
            content (list): List of Card objects to display as tab content.
                Each Card in the list will become a separate tab.

        Raises:
            AssertionError: If content is not a list or if any item in the list
                is not a Card object.
        """
        self.id = id
        self.title = title

        assert isinstance(content, list), "Content must be a list"
        assert all([isinstance(card, Card) for card in content]), (
            "Every entry must be a card"
        )

        self.content = content

    def to_html(self, initial_tab=None) -> str:
        """
        Serialize the tabs component into HTML using the built-in templates.

        This method generates the complete HTML structure for the tabbed interface,
        including the tab navigation buttons and content areas. It handles setting
        the active tab based on the initial_tab parameter or defaults to the first tab.

        Args:
            initial_tab (Enum, optional): Enum value specifying which tab should be
                initially active when the dashboard loads. The enum value should match
                one of the Card IDs in the content list. If None, the first tab will
                be active by default.

        Returns:
            str: Complete HTML representation of the tabbed interface, wrapped in a Card.
        """

        tabs = []
        content = []

        for idx, card in enumerate(self.content):
            tabs_d = {
                "tab_name": card.title,
                "href": card.id,
                "class": "",
            }
            content_d = {
                "tab_name": card.title,
                "content": card.html_content,
                "id": card.id,
                "class": "",
            }

            set_tab_to_active = (
                initial_tab is not None and card.id == initial_tab.value
            ) or (initial_tab is None and idx == 0)
            if set_tab_to_active:
                tabs_d["class"] = "active"
                content_d["class"] = "show active"

            tabs.append(self.t_tab_template.render(tabs_d))
            content.append(self.t_tab_content_template.render(content_d))

        html = self.t_top_template.render(
            {"tabs": "".join(tabs), "content": "".join(content)}
        )
        card = Card(self.id, self.title, html)

        return card.to_html()
