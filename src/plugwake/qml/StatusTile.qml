import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: tile

    property string title
    property string value
    property bool known: true
    property bool good: false

    readonly property bool dark: Application.styleHints.colorScheme === Qt.Dark

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
            visible: tile.known
            width: 10
            height: 10
            radius: 5
            color: tile.good ? (tile.dark ? "#6ccb5f" : "#0f7b0f") : (tile.dark ? "#9d9d9d" : "#8a8a8a")
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
