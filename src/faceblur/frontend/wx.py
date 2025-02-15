# Copyright (C) 2025, Simona Dimitrova

import argparse
import os
import sys
import threading
import wx

from faceblur.app import get_supported_filenames
from faceblur.app import faceblur
from faceblur.faces.deidentify import MODES as BLUR_MODES
from faceblur.faces.deidentify import STRENGTH as DEFAULT_STRENGTH
from faceblur.faces.dlib import MODELS as DLIB_MODELS
from faceblur.faces.dlib import UPSCALE as DEFAULT_UPSCALE
from faceblur.help import APP as APP_HELP
from faceblur.help import INPUTS as INPUTS_HELP
from faceblur.help import OUTPUT as OUTPUT_HELP
from faceblur.help import MODEL as MODEL_HELP
from faceblur.help import MODEL_MEDIAPIPE_CONFIDENCE as CONFIDENCE_HELP
from faceblur.help import MODEL_DLIB_UPSCALING as UPSCALING_HELP
from faceblur.help import TRACKING_MINIMUM_IOU as IOU_HELP
from faceblur.help import TRACKING_MAX_FACE_ENCODING_DISTANCE as ENCODING_HELP
from faceblur.help import TRACKING_DURATION as TRACKING_DURATION_HELP
from faceblur.help import TRACKING_MIN_FACE_DURATION as MIN_FACE_DURATION_HELP
from faceblur.help import MODE as MODE_HELP
from faceblur.help import BLUR_STRENGTH as STRENGTH_HELP
from faceblur.help import IMAGE_FORMAT as IMAGE_FORMAT_HELP
from faceblur.help import VIDEO_FORMAT as VIDEO_FORMAT_HELP
from faceblur.help import VIDEO_ENCODER as VIDEO_ENCODER_HELP
from faceblur.help import THREAD_TYPE as THREAD_TYPE_HELP
from faceblur.help import THREADS as THREADS_HELP
from faceblur.help import VERBOSE as VERBOSE_HELP
from faceblur.image import FORMATS as IMAGE_FORMATS
from faceblur.faces.mediapipe import MODELS as MP_MODELS
from faceblur.faces.mediapipe import CONFIDENCE as DEFAULT_CONFIDENCE
from faceblur.faces.mode import Mode, DEFAULT as DEFAULT_MODE
from faceblur.faces.model import Model, DEFAULT as DEFAULT_MODEL
from faceblur.faces.process import TRACKING_DURATION, MIN_FACE_DURATION
from faceblur.faces.track import IOU_MIN_OVERLAP, ENCODING_MAX_DISTANCE
from faceblur.progress import Progress
from faceblur.threading import TerminatingCookie


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


class ProgressWrapper(Progress):
    def __init__(self, progress, status):
        self._progress = progress
        self._status = status

    def __call__(self, desc=None, total=None, leave=True, unit=None):
        wx.CallAfter(self._set_all, total, desc)
        return self

    def _set_all(self, total, status):
        self._progress.SetRange(total)
        self._status.SetLabel(status if status else "")
        self._status.GetParent().Layout()

    def set_description(self, description):
        wx.CallAfter(self._set_status, description)

    def _set_status(self, status):
        self._status.SetLabel(status if status else "")
        self._status.GetParent().Layout()

    def update(self, n=1):
        wx.CallAfter(self._update, n)

    def _update(self, n):
        self._progress.SetValue(self._progress.GetValue() + n)

    def _clear(self):
        self._progress.SetValue(0)
        self._status.SetLabel("")

    def __exit__(self, exc_type, exc_value, traceback):
        wx.CallAfter(self._clear)


class ProgressDialog(wx.Dialog):
    def __init__(self, window, title):
        super().__init__(window, title=title, size=(600, 250), style=wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX)

        self._window = window

        # Main vertical layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # First progress bar and text
        file_progress_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._file_progress_text = wx.StaticText(self, label="Processing...", style=wx.ST_ELLIPSIZE_END)
        self._file_progress_text.SetMinSize((200, -1))
        self._file_progress_text.SetMaxSize((200, -1))
        self._file_progress_bar = wx.Gauge(self, style=wx.GA_SMOOTH | wx.GA_TEXT)
        file_progress_sizer.Add(self._file_progress_text, flag=wx.RIGHT, border=10)
        file_progress_sizer.Add(self._file_progress_bar, proportion=1)

        # Second progress bar and text
        total_progress_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._total_progress_text = wx.StaticText(self, label="Processing...", style=wx.ST_ELLIPSIZE_END)
        self._total_progress_text.SetMinSize((200, -1))
        self._total_progress_text.SetMaxSize((200, -1))
        self._total_progress_bar = wx.Gauge(self, style=wx.GA_SMOOTH | wx.GA_TEXT | wx.GA_PROGRESS)
        total_progress_sizer.Add(self._total_progress_text, flag=wx.RIGHT, border=10)
        total_progress_sizer.Add(self._total_progress_bar, proportion=1)

        # Cancel button
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        cancel_button = wx.Button(self, label="Cancel")
        cancel_button.SetDefault()
        button_sizer.Add(cancel_button, flag=wx.ALIGN_LEFT)

        # Bind the cancel button to close the dialog
        cancel_button.Bind(wx.EVT_BUTTON, self._on_cancel)

        # Add components to main_sizer
        main_sizer.Add(total_progress_sizer, flag=wx.EXPAND | wx.ALL, border=15)
        main_sizer.Add(file_progress_sizer, flag=wx.EXPAND | wx.ALL, border=15)
        main_sizer.Add(button_sizer, flag=wx.ALIGN_LEFT | wx.ALL, border=15)

        # Set sizer for the dialog
        self.SetMinSize((600, -1))
        self.SetSizer(main_sizer)
        self.Fit()

    @property
    def progress_total(self):
        return self._total_progress_bar, self._total_progress_text

    @property
    def progress_file(self):
        return self._file_progress_bar, self._file_progress_text

    def _on_cancel(self, event):
        assert self._window._cookie
        self._window._cookie.requestTermination()


class MainWindow(wx.Frame):
    def __init__(self, parent, title, verbose):
        super().__init__(parent, title=title, size=(600, 400))

        self._verbose = verbose
        self._thread = None
        self._cookie = None

        # Create menu
        menu = wx.MenuBar()

        # Add Exit to File menu on non-MacOS
        if sys.platform != "darwin":
            file_menu = wx.Menu()
            menu.Append(file_menu, "&File")
            file_menu.Append(wx.ID_EXIT)
            self.Bind(wx.EVT_MENU, self._quit, id=wx.ID_EXIT)

        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "", "About this application")
        menu.Append(help_menu, "&Help")

        # Bind events
        self.Bind(wx.EVT_MENU, self._about, id=wx.ID_ABOUT)

        self.SetMenuBar(menu)

        # Main panel and sizer
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # List of files on the left
        self._file_list = wx.ListBox(panel, style=wx.LB_EXTENDED)
        self._file_list.SetMinSize((400, -1))
        self._file_list.Bind(wx.EVT_KEY_DOWN, self._list_on_key_down)
        main_sizer.Add(self._file_list, 1, wx.EXPAND | wx.ALL, 5)

        def add_element(element, panel, sizer, label=None, tooltip=None):
            if tooltip:
                element.SetToolTip(wx.ToolTip(tooltip.strip()))

            if label:
                if isinstance(label, str):
                    label = wx.StaticText(panel, label=label)

                if tooltip:
                    # Need a new instace of tooltip for the label
                    # otherwise wxPython does a double-free on close
                    label.SetToolTip(wx.ToolTip(tooltip.strip()))

                # Add the label to the UI
                sizer.Add(label, 0, wx.LEFT | wx.TOP, 5)

            # Add the element to the UI
            sizer.Add(element, 0, wx.EXPAND | wx.ALL, 5)

        # Right panel
        right_panel = wx.Panel(panel)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Panel containing all options
        options_panel = wx.StaticBox(right_panel, label="Options")
        options_sizer = wx.StaticBoxSizer(options_panel, wx.VERTICAL)

        # Models

        # Panel containg model options
        model_options_panel = wx.StaticBox(right_panel, label="Model")
        model_options_sizer = wx.StaticBoxSizer(model_options_panel, wx.VERTICAL)
        options_sizer.Add(model_options_sizer, flag=wx.ALL | wx.EXPAND, border=10)

        self._model = wx.ComboBox(
            model_options_panel, value=DEFAULT_MODEL, choices=list(Model),
            style=wx.CB_READONLY | wx.CB_DROPDOWN)
        self._model.Bind(wx.EVT_COMBOBOX, self._update_model_options)
        add_element(self._model, model_options_panel, model_options_sizer, "Detection model", MODEL_HELP)

        self._mp_confidence_label = wx.StaticText(model_options_panel, label="Detection confidence (%)")
        self._mp_confidence = wx.SpinCtrl(model_options_panel, value=str(DEFAULT_CONFIDENCE))
        add_element(self._mp_confidence, model_options_panel, model_options_sizer,
                    self._mp_confidence_label, CONFIDENCE_HELP)

        self._dlib_upscale_label = wx.StaticText(model_options_panel, label="Detection upscale (x)")
        self._dlib_upscale = wx.SpinCtrl(model_options_panel, value=str(DEFAULT_UPSCALE), min=1, max=8)
        add_element(self._dlib_upscale, model_options_panel, model_options_sizer,
                    self._dlib_upscale_label, UPSCALING_HELP)

        # Panel containg tracking options
        tracking_options_panel = wx.StaticBox(right_panel, label="Face tracking")
        tracking_options_sizer = wx.StaticBoxSizer(tracking_options_panel, wx.VERTICAL)
        options_sizer.Add(tracking_options_sizer, flag=wx.ALL | wx.EXPAND, border=10)

        self._tracking = wx.CheckBox(tracking_options_panel, label="Enabled")
        self._tracking.SetValue(True)
        self._tracking.Bind(wx.EVT_CHECKBOX, self._on_tracking)
        self._tracking.SetToolTip(wx.ToolTip("Enable face tracking used to do extra processing on faces for videos"))
        tracking_options_sizer.Add(self._tracking, 0, wx.EXPAND | wx.ALL, 5)

        self._iou_min_overlap_label = wx.StaticText(tracking_options_panel, label="Min overlap for IoU (%)")
        self._iou_min_overlap = wx.SpinCtrl(tracking_options_panel, value=str(IOU_MIN_OVERLAP))
        add_element(self._iou_min_overlap, tracking_options_panel, tracking_options_sizer,
                    self._iou_min_overlap_label, IOU_HELP)

        self._encoding_max_distance_label = wx.StaticText(tracking_options_panel, label="Max encoding distance (%)")
        self._encoding_max_distance = wx.SpinCtrlDouble(tracking_options_panel, value=str(ENCODING_MAX_DISTANCE))
        add_element(self._encoding_max_distance, tracking_options_panel, tracking_options_sizer,
                    self._encoding_max_distance_label, ENCODING_HELP)

        self._min_track_face_duration_label = wx.StaticText(tracking_options_panel, label="Min face duration (s)")
        self._min_track_face_duration = wx.SpinCtrlDouble(
            tracking_options_panel, value=str(MIN_FACE_DURATION),
            min=0, max=10, inc=0.1)
        add_element(self._min_track_face_duration, tracking_options_panel, tracking_options_sizer,
                    self._min_track_face_duration_label, MIN_FACE_DURATION_HELP)

        self._tracking_duration_label = wx.StaticText(tracking_options_panel, label="Tracking duration (s)")
        self._tracking_duration = wx.SpinCtrlDouble(
            tracking_options_panel, value=str(TRACKING_DURATION), min=0, max=10, inc=0.1)
        add_element(self._tracking_duration, tracking_options_panel, tracking_options_sizer,
                    self._tracking_duration_label, TRACKING_DURATION_HELP)

        self._tracking_controls = [
            self._iou_min_overlap_label,
            self._iou_min_overlap,
            self._encoding_max_distance_label,
            self._encoding_max_distance,
            self._min_track_face_duration_label,
            self._min_track_face_duration,
            self._tracking_duration_label,
            self._tracking_duration,
        ]

        mp_controls = [
            self._mp_confidence_label,
            self._mp_confidence,
            self._iou_min_overlap_label,
            self._iou_min_overlap,
        ]

        dlib_controls = [
            self._dlib_upscale_label,
            self._dlib_upscale,
            self._encoding_max_distance_label,
            self._encoding_max_distance,
        ]

        self._model_options_controls = {
            Model.MEDIA_PIPE_SHORT_RANGE: mp_controls,
            Model.MEDIA_PIPE_FULL_RANGE: mp_controls,
            Model.DLIB_HOG: dlib_controls,
            Model.DLIB_CNN: dlib_controls,
        }

        # Modes

        # Panel containg mode options
        mode_options_panel = wx.StaticBox(right_panel, label="Mode")
        mode_options_sizer = wx.StaticBoxSizer(mode_options_panel, wx.VERTICAL)
        options_sizer.Add(mode_options_sizer, flag=wx.ALL | wx.EXPAND, border=10)

        self._mode = wx.ComboBox(
            mode_options_panel, value=DEFAULT_MODE, choices=list(Mode),
            style=wx.CB_READONLY | wx.CB_DROPDOWN)
        self._mode.Bind(wx.EVT_COMBOBOX, self._update_mode_options)
        add_element(self._mode, mode_options_panel, mode_options_sizer, "Mode", MODE_HELP)

        self._strength_label = wx.StaticText(mode_options_panel, label="Blur strength (%)")
        self._strength = wx.SpinCtrl(mode_options_panel, value=str(DEFAULT_STRENGTH), min=1, max=1000)
        add_element(self._strength, mode_options_panel, mode_options_sizer,
                    self._strength_label, STRENGTH_HELP)

        self._mode_options_controls = {
            Mode.DEBUG: [],
            Mode.RECT_BLUR: [
                self._strength_label,
                self._strength,
            ],
            Mode.GRACEFUL_BLUR: [
                self._strength_label,
                self._strength,
            ],
        }

        # Reset button
        reset_button = wx.Button(options_panel, label="Reset options")
        reset_button.Bind(wx.EVT_BUTTON, self._on_reset)
        options_sizer.Add(reset_button, 0, wx.EXPAND | wx.ALL, 5)

        # End of options panel
        right_sizer.Add(options_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Output field
        output_panel = wx.StaticBox(right_panel, label="Output")
        output_sizer = wx.StaticBoxSizer(output_panel, wx.HORIZONTAL)

        self._output = wx.TextCtrl(output_panel)
        output_sizer.Add(self._output, flag=wx.RIGHT, border=10, proportion=5)

        browse_button = wx.Button(output_panel, label="Browse")
        browse_button.Bind(wx.EVT_BUTTON, self._on_browse)
        output_sizer.Add(browse_button, proportion=1)

        right_sizer.Add(output_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Start button
        start_button = wx.Button(right_panel, label="Start")
        start_button.Bind(wx.EVT_BUTTON, self._on_start)
        start_button.SetDefault()
        right_sizer.Add(start_button, 0, wx.EXPAND | wx.ALL, 5)

        right_panel.SetSizer(right_sizer)
        main_sizer.Add(right_panel, 0, wx.EXPAND | wx.ALL, 5)

        # Set the main panel sizer
        panel.SetSizer(main_sizer)

        # Add a top-level sizer to make sure all vertical elements
        # are visible by default
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(panel, 1, wx.EXPAND | wx.ALL)
        self.SetSizerAndFit(top_sizer)

        # Support drag & drop
        self.SetDropTarget(Drop(self))

        # Update visibility on options
        self._update_model_options()
        self._update_mode_options()

        # Show the window
        self.Centre()
        self.Show()

    def _quit(self, event):
        self.Close()

    def _about(self, event):
        message = """
Faceblur is a Python library and command-line tool to obfuscate faces from photos and videos via blurring them.

It uses the av package to access FFmpeg functionality, and pymediainfo to obtain file and stream metadata, that is not yet available through av (even though it is available in FFmpeg).

Licensed under BSD 3-Clause.

Copyright (C) 2025, Simona Dimitrova"""
        wx.MessageDialog(None, message, "About", wx.OK | wx.CENTER | wx.ICON_INFORMATION).ShowModal()

    def _update_options(self, options, value):
        # Hide all
        for cs in options.values():
            for c in cs:
                c.Hide()

        # Show only relevant ones
        if value in options:
            for c in options[value]:
                c.Show()

        self.Layout()

    def _update_model_options(self, event=None):
        self._update_options(self._model_options_controls, self._model.GetValue())

    def _update_mode_options(self, event=None):
        self._update_options(self._mode_options_controls, self._mode.GetValue())

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

    def _on_reset(self, event):
        self._model.SetValue(DEFAULT_MODEL)
        self._mp_confidence.SetValue(DEFAULT_CONFIDENCE)
        self._dlib_upscale.SetValue(1)
        self._iou_min_overlap.SetValue(IOU_MIN_OVERLAP)
        self._encoding_max_distance.SetValue(ENCODING_MAX_DISTANCE)
        self._min_track_face_duration.SetValue(MIN_FACE_DURATION)
        self._tracking_duration.SetValue(TRACKING_DURATION)
        self._mode.SetValue(DEFAULT_MODE)
        self._strength.SetValue(DEFAULT_STRENGTH)
        self._tracking.SetValue(True)
        self._on_tracking()
        self._update_model_options()
        self._update_mode_options()

    def _on_tracking(self, event=None):
        enable = self._tracking.GetValue()
        for control in self._tracking_controls:
            control.Enable(enable)

    def _on_browse(self, event):
        with wx.DirDialog(None, "Output folder", style=wx.DD_DEFAULT_STYLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._output.SetValue(dlg.GetPath())
                self._output.GetParent().Layout()

    def _remove_file(self, filename):
        for index, f in enumerate(self._file_list.GetItems()):
            if f == filename:
                self._file_list.Delete(index)

                # Assumes no duplicates in the list
                break

    def _thread_done(self):
        assert self._thread
        assert self._progress

        self._thread.join()
        self._cookie = None
        self._thread = None

        self._progress.Close()

    def _on_done(self, filename):
        if filename:
            # 1 file has finished. Remove it from the list
            wx.CallAfter(self._remove_file, filename)
        else:
            # All files have finished
            wx.CallAfter(self._thread_done)

    def _handle_error(self, ex, filename):
        ex = str(ex) if ex else "Unknown error"
        wx.MessageDialog(None, f"An error occured wile processing {filename}: {ex}", "Error",
                         wx.OK | wx.CENTER | wx.ICON_ERROR).ShowModal()

        self._thread_done()

    def _on_error(self, ex, filename):
        wx.CallAfter(self._handle_error, ex, filename)

    def _on_start(self, event):
        assert not self._thread
        assert not self._cookie

        if not self._file_list.GetCount():
            # Nothing to do
            wx.MessageDialog(None, "Please, select files for processing.", "Error",
                             wx.OK | wx.CENTER | wx.ICON_ERROR).ShowModal()
            return

        if not self._output.GetValue():
            self._on_browse(None)

        if not os.path.isdir(self._output.GetValue()):
            wx.MessageDialog(None, f"Selected output {self._output.GetValue(
            )} is not an existing folder.", "Error", wx.OK | wx.CENTER | wx.ICON_ERROR).ShowModal()
            return

        self._cookie = TerminatingCookie()

        self._progress = ProgressDialog(self, "Working...")

        tracking = {
            "min_face_duration": self._min_track_face_duration.GetValue(),
            "tracking_duration": self._tracking_duration.GetValue(),
        }

        model_options = {}
        if self._model.GetValue() in MP_MODELS:
            model_options["confidence"] = self._mp_confidence.GetValue()
            tracking["score"] = self._iou_min_overlap.GetValue()

        if self._model.GetValue() in DLIB_MODELS:
            model_options["upscale"] = self._dlib_upscale.GetValue()
            tracking["score"] = self._encoding_max_distance.GetValue()

        mode_options = {}
        if self._mode.GetValue() in BLUR_MODES:
            mode_options["strength"] = self._strength.GetValue()

        kwargs = {
            "inputs": self._file_list.GetItems(),
            "output": self._output.GetValue(),
            "model": self._model.GetValue(),
            "model_options": model_options,
            "tracking_options": tracking if self._tracking.GetValue() else False,
            "mode": self._mode.GetValue(),
            "mode_options": mode_options,
            "on_done": self._on_done,
            "on_error": self._on_error,
            "stop": self._cookie,
            "total_progress": ProgressWrapper(*self._progress.progress_total),
            "file_progress": ProgressWrapper(*self._progress.progress_file),
            "verbose": self._verbose,
        }

        self._thread = threading.Thread(target=faceblur, kwargs=kwargs)
        self._thread.start()

        self._progress.ShowModal()


def main():
    parser = argparse.ArgumentParser(
        description="A tool to obfuscate faces from photos and videos via blurring them."
    )

    parser.add_argument("--verbose", "-v",
                        action="store_true",
                        help="Enable verbose logging from all components.")

    args = parser.parse_args()

    app = wx.App(False)
    frame = MainWindow(None, "FaceBlur: Automatic Photo and Video Deidentifier", args.verbose)
    app.MainLoop()


if __name__ == "__main__":
    main()
