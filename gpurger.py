#!/usr/bin/env python3
import json
import os
import sys

import gi
import requests

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk


class MyWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set app name
        GLib.set_application_name("GPurger")

        self.set_margin_top(20)
        self.set_margin_bottom(10)
        self.set_default_size(900, 500)

        # Create a box to hold the URL entry and button
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(box)

        # Create a label for the URL entry
        url_label = Gtk.Label(label="Enter URL to purge:")
        box.append(url_label)

        # Create an entry for the URL
        self.url_entry = Gtk.Entry()
        self.url_entry.set_text("https://www.cbc.ca/")
        box.append(self.url_entry)

        # Create a button to purge the URL
        purge_button = Gtk.Button.new_with_label("Purge")
        purge_button.connect("clicked", self.on_purge_clicked)
        box.append(purge_button)

        # Create a status bar to display messages to the user
        self.statusbar = Gtk.Statusbar()
        box.append(self.statusbar)

    def on_purge_clicked(self, button):
        url = self.url_entry.get_text()
        auth_token = os.environ.get("PURGER_TOKEN")

        if not auth_token:
            self.statusbar.push(
                0,
                "Authorization token not found. Please set the PURGER_TOKEN environment variable.",
            )
        elif not url.startswith("http"):
            self.statusbar.push(0, f"Invalid URL: {url}")
        else:
            # Show confirmation dialog before purging the URL
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text="Are you sure you want to purge this URL?",
            )
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
                purge_urls([url], auth_token)
                self.statusbar.push(0, "Purge request successful.")
            else:
                self.statusbar.push(0, "Purge request cancelled.")


class GPurgerApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.window = MyWindow(application=app)
        self.window.present()
        self.window.show()

        # Create a menu bar
        menubar = Gtk.MenuBar()
        appmenu = Gtk.Menu()
        helpmenu = Gtk.Menu()

        # Add options to the app menu
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.on_quit)
        appmenu.append(quit_item)

        # Add options to the help menu
        help_item = Gtk.MenuItem(label="Help")
        help_item.connect("activate", self.on_help)
        helpmenu.append(help_item)

        # Add menus to the menu bar
        appmenu_item = Gtk.MenuItem(label="GPurger")
        appmenu_item.set_submenu(appmenu)
        menubar.append(appmenu_item)

        helpmenu_item = Gtk.MenuItem(label="Help")
        helpmenu_item.set_submenu(helpmenu)
        menubar.append(helpmenu_item)

        # Add the menu bar to the window
        self.window.set_titlebar(menubar)

    def on_quit(self, widget):
        self.quit()

    def on_help(self, widget):
        # Open help page in default web browser
        Gio.AppInfo.launch_default_for_uri("https://example.com/help", None)


def purge_urls(url_list, auth_token):
    """
    Purge the specified URLs using the given auth token.

    Args:
        url_list (list): List of URLs to purge.
        auth_token (str): Authorization token.

    Returns:
        None
    """
    headers = {"Authorization": f"Basic {auth_token}", "Content-Type": "application/json"}
    payload = {"url": url_list}
    url = "https://webops01.nm.cbc.ca/purger/api/v1/purge/prod"

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for non-2xx status codes

        print("Purge request successful.")
        print(response.text)
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"Purge request failed: {e}")


if __name__ == "__main__":
    """
    This script purges URLs from the CBC web cache using the CBC Purger API.
    """
    app = GPurgerApp()
    app.register()
    app.run(sys.argv)

