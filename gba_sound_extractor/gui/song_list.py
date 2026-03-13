"""Sortable song list widget with tag columns."""

from PyQt5.QtWidgets import (QTableView, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import (pyqtSignal, Qt, QSortFilterProxyModel,
                           QAbstractTableModel, QModelIndex, QVariant)
from PyQt5.QtGui import QColor

from ..mp2k.structures import Song


# Column indices
COL_INDEX = 0
COL_NAME = 1
COL_CATEGORY = 2
COL_TRACKS = 3
COL_DURATION = 4
COL_TEMPO = 5
COL_LOOP = 6
COL_INSTRUMENTS = 7
_COLUMN_COUNT = 8

_HEADERS = ["#", "Name", "Category", "Tracks", "Duration",
            "Tempo", "Loop", "Instruments"]

# Category colour coding (dark theme)
_CATEGORY_COLORS = {
    "Music":   QColor(26, 46, 74),      # dark blue
    "SFX":     QColor(42, 42, 42),      # dark grey
    "Jingle":  QColor(58, 53, 32),      # dark amber
    "Fanfare": QColor(26, 58, 26),      # dark green
}

_CATEGORY_TEXT_COLORS = {
    "Music":   QColor(91, 160, 240),    # #5ba0f0
    "SFX":     QColor(153, 153, 153),   # #999999
    "Jingle":  QColor(212, 184, 74),    # #d4b84a
    "Fanfare": QColor(90, 192, 90),     # #5ac05a
}


def _format_duration(secs):
    """Format seconds as M:SS."""
    if secs <= 0:
        return "0:00"
    m = int(secs) // 60
    s = int(secs) % 60
    return f"{m}:{s:02d}"


class SongTableModel(QAbstractTableModel):
    """Flat table model backed by a list of Song objects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._songs = []

    def set_songs(self, songs):
        self.beginResetModel()
        self._songs = list(songs)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._songs = []
        self.endResetModel()

    def song_at(self, row):
        if 0 <= row < len(self._songs):
            return self._songs[row]
        return None

    # ---- QAbstractTableModel overrides ----

    def rowCount(self, parent=QModelIndex()):
        return len(self._songs)

    def columnCount(self, parent=QModelIndex()):
        return _COLUMN_COUNT

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(_HEADERS):
                return _HEADERS[section]
        return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        row, col = index.row(), index.column()
        if row < 0 or row >= len(self._songs):
            return QVariant()

        song = self._songs[row]

        if role == Qt.DisplayRole:
            return self._display_data(song, col)

        if role == Qt.TextAlignmentRole:
            if col in (COL_INDEX, COL_TRACKS, COL_DURATION, COL_TEMPO):
                return Qt.AlignCenter
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == Qt.BackgroundRole and col == COL_CATEGORY:
            color = _CATEGORY_COLORS.get(song.category)
            if color:
                return color

        if role == Qt.ForegroundRole and col == COL_CATEGORY:
            color = _CATEGORY_TEXT_COLORS.get(song.category)
            if color:
                return color

        # For sorting: store raw sortable values in UserRole
        if role == Qt.UserRole:
            return self._sort_data(song, col)

        return QVariant()

    def _display_data(self, song, col):
        if col == COL_INDEX:
            return str(song.index)
        if col == COL_NAME:
            return song.name
        if col == COL_CATEGORY:
            return song.category or ""
        if col == COL_TRACKS:
            return str(song.num_tracks)
        if col == COL_DURATION:
            return _format_duration(song.duration_secs) if song.duration_secs > 0 else ""
        if col == COL_TEMPO:
            if song.tempo_bpm > 0:
                return f"{song.tempo_bpm} ({song.tempo_label})"
            return ""
        if col == COL_LOOP:
            return song.loop_status or ""
        if col == COL_INSTRUMENTS:
            return song.instrument_profile or ""
        return ""

    def _sort_data(self, song, col):
        """Return a sortable value for a given column."""
        if col == COL_INDEX:
            return song.index
        if col == COL_NAME:
            return song.name.lower()
        if col == COL_CATEGORY:
            return song.category or ""
        if col == COL_TRACKS:
            return song.num_tracks
        if col == COL_DURATION:
            return song.duration_secs
        if col == COL_TEMPO:
            return song.tempo_bpm
        if col == COL_LOOP:
            return 0 if song.loop_status == "Looping" else 1
        if col == COL_INSTRUMENTS:
            return song.instrument_profile or ""
        return ""

    def refresh(self):
        """Notify the view that all data has changed (e.g. after tagging)."""
        top_left = self.index(0, 0)
        bottom_right = self.index(self.rowCount() - 1, _COLUMN_COUNT - 1)
        self.dataChanged.emit(top_left, bottom_right)


class SongSortProxy(QSortFilterProxyModel):
    """Proxy that sorts using the UserRole (raw numeric/comparable data)."""

    def lessThan(self, left, right):
        l_data = self.sourceModel().data(left, Qt.UserRole)
        r_data = self.sourceModel().data(right, Qt.UserRole)
        # Handle None / QVariant mismatches gracefully
        try:
            return l_data < r_data
        except TypeError:
            return str(l_data) < str(r_data)


class SongListWidget(QTableView):
    """Table showing all songs found in the ROM with sortable columns."""

    song_selected = pyqtSignal(int)       # Emits song index
    song_double_clicked = pyqtSignal(int)  # Emits song index for preview

    def __init__(self, parent=None):
        super().__init__(parent)
        self._songs = []

        # Model stack
        self._model = SongTableModel(self)
        self._proxy = SongSortProxy(self)
        self._proxy.setSourceModel(self._model)
        self.setModel(self._proxy)

        # Appearance
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)

        # Column sizing
        header = self.horizontalHeader()
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        for col in (COL_INDEX, COL_TRACKS, COL_DURATION, COL_TEMPO,
                     COL_LOOP, COL_CATEGORY, COL_INSTRUMENTS):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Signals
        self.selectionModel().selectionChanged.connect(
            self._on_selection_changed)
        self.doubleClicked.connect(self._on_double_click)

        # Default sort
        self.sortByColumn(COL_INDEX, Qt.AscendingOrder)

    def set_songs(self, songs):
        """Populate the table with Song objects."""
        self._songs = songs
        self._model.set_songs(songs)

    def clear_songs(self):
        self._songs = []
        self._model.clear()

    def refresh(self):
        """Refresh the display after tags have been updated."""
        self._model.refresh()

    def get_selected_indices(self):
        """Return list of selected song indices."""
        indices = set()
        for idx in self.selectionModel().selectedRows():
            source_idx = self._proxy.mapToSource(idx)
            song = self._model.song_at(source_idx.row())
            if song is not None:
                indices.add(song.index)
        return sorted(indices)

    def _on_selection_changed(self, selected, deselected):
        rows = self.selectionModel().selectedRows()
        if len(rows) == 1:
            source_idx = self._proxy.mapToSource(rows[0])
            song = self._model.song_at(source_idx.row())
            if song is not None:
                self.song_selected.emit(song.index)

    def _on_double_click(self, proxy_index):
        source_idx = self._proxy.mapToSource(proxy_index)
        song = self._model.song_at(source_idx.row())
        if song is not None:
            self.song_double_clicked.emit(song.index)
