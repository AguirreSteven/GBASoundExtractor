"""GBA Sound Extractor — Extract music from GBA ROMs as MIDI files."""

import sys
import logging

from PyQt5.QtWidgets import QApplication
from gba_sound_extractor.gui.main_window import MainWindow


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("GBA Sound Extractor")
    app.setStyle("Fusion")

    from gba_sound_extractor.gui.theme import apply_dark_theme
    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
