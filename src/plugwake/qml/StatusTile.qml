import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: tile

    property string title
    property string value
    // good: all on, warn: needs attention, off: plainly off, empty: unknown (no dot)
    property string tone: ""

    readonly property bool dark: Application.styleHints.colorScheme === Qt.Dark
    readonly property var toneColors: ({
            "good": dark ? "#6ccb5f" : "#0f7b0f",
            "warn": dark ? "#ffa94d" : "#c25e00",
            "off": dark ? "#9d9d9d" : "#8a8a8a"
        })

    Layout.fillWidth: true
    spacing: 4

    Label {
        Layout.fillWidth: true
        text: tile.title
        opacity: 0.7
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        Rectangle {
            visible: tile.tone !== ""
            width: 10
            height: 10
            radius: 5
            color: tile.toneColors[tile.tone] || "transparent"
        }
        Label {
            Layout.fillWidth: true
            elide: Text.ElideRight
            text: tile.value
            font.pixelSize: 18
            font.weight: Font.DemiBold
        }
    }
}
