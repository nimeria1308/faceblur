# Copyright (C) 2025, Simona Dimitrova

import os
import wx

from faceblur.app import get_supported_filenames


class Drop(wx.FileDropTarget):
    def __init__(self, window):
        super().__init__()
        self._window = window

    def OnDropFiles(self, x, y, filenames):
        def on_error(message):
            wx.MessageDialog(None, message, "Warning", wx.OK | wx.CENTER | wx.ICON_WARNING).ShowModal()
        filenames = get_supported_filenames(filenames, on_error)

        for filename in filenames:
            filename = os.path.abspath(filename)

            # Add only if not added by the user before
            if filename not in self._window._file_list.GetItems():
                self._window._file_list.Append(filename)

        return True


DEFAULT_STRENGTH = 1.0
DEFAULT_CONFIDENCE = 0.5


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(600, 400))

        # Main panel and sizer
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # List of files on the left
        self._file_list = wx.ListBox(panel, style=wx.LB_EXTENDED)
        self._file_list.Bind(wx.EVT_KEY_DOWN, self._list_on_key_down)
        main_sizer.Add(self._file_list, 1, wx.EXPAND | wx.ALL, 5)

        # Right panel
        right_panel = wx.Panel(panel)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        # "Options" Panel with number inputs
        options_panel = wx.StaticBox(right_panel, label="Options")
        options_sizer = wx.StaticBoxSizer(options_panel, wx.VERTICAL)

        self._strength = wx.SpinCtrlDouble(right_panel, value=str(DEFAULT_STRENGTH), min=0, max=10, inc=0.1)
        options_sizer.Add(wx.StaticText(right_panel, label="Blur strength"), 0, wx.LEFT | wx.TOP, 5)
        options_sizer.Add(self._strength, 0, wx.EXPAND | wx.ALL, 5)

        self._confidence = wx.SpinCtrlDouble(right_panel, value=str(DEFAULT_CONFIDENCE), min=0, max=1, inc=0.01)
        options_sizer.Add(wx.StaticText(right_panel, label="Detection confidence"), 0, wx.LEFT | wx.TOP, 5)
        options_sizer.Add(self._confidence, 0, wx.EXPAND | wx.ALL, 5)

        right_sizer.Add(options_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Button(s) on the right
        button_panel = wx.Panel(right_panel)
        button_sizer = wx.BoxSizer(wx.VERTICAL)

        self._reset_button = wx.Button(button_panel, label="Reset")
        self._start_button = wx.Button(button_panel, label="Start")
        self._start_button.SetDefault()
        self._buttons = [
            self._reset_button,
            self._start_button,
        ]

        for button in self._buttons:
            button_sizer.Add(button, 0, wx.EXPAND | wx.ALL, 5)

        button_panel.SetSizer(button_sizer)
        right_sizer.Add(button_panel, 0, wx.EXPAND | wx.ALL, 5)

        right_panel.SetSizer(right_sizer)
        main_sizer.Add(right_panel, 0, wx.EXPAND | wx.ALL, 5)

        # Set the main panel sizer
        panel.SetSizer(main_sizer)

        # Add a status bar with progress bars
        self._status_bar = wx.StatusBar(self)
        self.SetStatusBar(self._status_bar)

        # Create 3 fields in the status bar
        self._status_bar.SetFieldsCount(3)
        self._status_bar.SetStatusWidths([-1, 150, 150])  # -1 = stretch, others fixed

        # Add progress bars to the last two fields
        self._progress_bar1 = wx.Gauge(self._status_bar)
        self._progress_bar2 = wx.Gauge(self._status_bar)

        # Position progress bars within the status bar
        self.Bind(wx.EVT_SIZE, self.on_resize_statusbar)  # Keep layout consistent during resizing
        self.position_progress_bars()

        # Simulate some progress changes
        self._progress_bar1.SetValue(60)
        self._progress_bar2.SetValue(30)

        # Support drag & drop
        self.SetDropTarget(Drop(self))

        # Show the window
        self.Centre()
        self.Show()

    def position_progress_bars(self):
        # Dynamically position progress bars based on the status bar's dimensions
        rect1 = self._status_bar.GetFieldRect(1)
        rect2 = self._status_bar.GetFieldRect(2)

        self._progress_bar1.SetSize(rect1)
        self._progress_bar1.SetPosition((rect1.x, rect1.y))
        self._progress_bar1.SetValue(0)

        self._progress_bar2.SetPosition((rect2.x + 5, rect2.y + (rect2.height - self._progress_bar2.GetSize()[1]) // 2))

    def on_resize_statusbar(self, event):
        self.position_progress_bars()
        event.Skip()

    def _list_on_key_down(self, event):
        # Check for Ctrl+A (Select All)
        if event.GetKeyCode() == ord('A') and event.ControlDown():
            # Select all items (one by one)
            for index in range(self._file_list.GetCount()):
                self._file_list.SetSelection(index)

        # Check if the Delete key is pressed
        elif event.GetKeyCode() == wx.WXK_DELETE:
            # Get a list of selected indices
            selections = self._file_list.GetSelections()
            if selections:
                # Reverse the selection order to avoid index shifting issues
                for index in reversed(selections):
                    self._file_list.Delete(index)
        else:
            # Pass other key events to the list box
            event.Skip()


def main():
    app = wx.App(False)
    frame = MainWindow(None, "FaceBlur: Automatic Photo and Video Deidentifier")
    app.MainLoop()


if __name__ == "__main__":
    main()
