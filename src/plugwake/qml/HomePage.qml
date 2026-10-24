import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page

    signal actionRequested(string actionId)

    readonly property color dangerColor: Application.styleHints.colorScheme === Qt.Dark ? "#ff99a4" : "#c42b1c"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        anchors.leftMargin: 16
        spacing: 12

        Label {
            text: "Home"
            font.pixelSize: 28
            font.weight: Font.DemiBold
        }

        Frame {
            Layout.fillWidth: true

            RowLayout {
                anchors.fill: parent
                spacing: 12

                Item {
                    visible: backend.running
                    Layout.preferredWidth: 32
                    Layout.maximumWidth: 32
                    Layout.preferredHeight: 32

                    BusyIndicator {
                        anchors.fill: parent
                        padding: 0
                        running: backend.running
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        Layout.fillWidth: true
                        text: "Status"
                        opacity: 0.7
                    }
                    Label {
                        Layout.fillWidth: true
                        text: backend.status
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Frame {
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                Label {
                    text: "Power"
                    font.weight: Font.DemiBold
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        Layout.fillWidth: true
                        text: "Remote On"
                        highlighted: true
                        enabled: !backend.running
                        onClicked: page.actionRequested("on")
                    }
                    Button {
                        Layout.fillWidth: true
                        text: "Remote Off"
                        enabled: !backend.running
                        onClicked: page.actionRequested("off")
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        text: "Soft Reboot"
                        enabled: !backend.running
                        onClicked: page.actionRequested("reboot")
                    }
                    Button {
                        text: "Hard Reboot"
                        enabled: !backend.running
                        palette.active.buttonText: page.dangerColor
                        palette.inactive.buttonText: page.dangerColor
                        onClicked: page.actionRequested("hard-reboot")
                    }
                    Item {
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "Test Home Assistant"
                        flat: true
                        enabled: !backend.running
                        onClicked: page.actionRequested("test-ha")
                    }
                    Button {
                        text: "Test RDP Port"
                        flat: true
                        enabled: !backend.running
                        onClicked: page.actionRequested("test-rdp")
                    }
                }
            }
        }

        Frame {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true

                    Label {
                        text: "Log"
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                    }
                    Button {
                        text: "Clear"
                        flat: true
                        onClicked: logArea.clear()
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TextArea {
                        id: logArea

                        readOnly: true
                        verticalAlignment: TextEdit.AlignTop
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                        font.family: "Consolas"
                    }
                }
            }
        }
    }

    Connections {
        target: backend

        function onLogLine(line) {
            logArea.append(line)
        }
    }
}
