#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication,
                             QWidget,
                             QHBoxLayout,
                             QVBoxLayout,
                             QTextEdit,
                             QLineEdit,
                             QTextBrowser)

from argparse import ArgumentParser
from quamash import QEventLoop, QThreadExecutor
from gitter import Room, coroutine


class Entry(QLineEdit):
    def __init__(self, room):
        self.room = room
        super().__init__()

    def keyPressEvent(self, e):
        if e.key() + 1 == Qt.Key_Enter:
            asyncio.ensure_future(self.room.send_message(self.text()))
            self.setText('')
        else:
            super().keyPressEvent(e)


class App(QWidget):
    def __init__(self, room):
        super().__init__()

        vbox = QVBoxLayout()
        self.text_browser = QTextBrowser()
        vbox.addWidget(self.text_browser)
        self.text_entry = Entry(room)
        self.text_entry.setFocus()
        vbox.addWidget(self.text_entry)
        self.setLayout(vbox)

        self.messages_future = None
        self._run(room)

    def closeEvent(self, e):
        if self.messages_future:
            self.messages_future.cancel()
        super().closeEvent(e)

    def _run(self, room):
        @coroutine
        def logger():
            while True:
                message = (yield)
                self.text_browser.append(message['text'])

        self.messages_future = asyncio.ensure_future(
            room.get_messages(logger()))


def gui_loop(room_uri):
    app = QApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    w = App(Room(room_uri))
    w.show()
    with loop:
        loop.run_forever()


def main():
    p = ArgumentParser()
    p.add_argument('room_uri', type=str)
    args = p.parse_args()
    gui_loop(args.room_uri)


if __name__ == "__main__":
    main()
