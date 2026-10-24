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

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    StatusTile {
                        readonly property string plug: backend.pcStatus.plug || ""

                        title: "Smart plug"
                        known: plug !== ""
                        good: plug === "on"
                        value: plug === "on" ? "On" : plug === "off" ? "Off" : "Unknown"
                    }
                    StatusTile {
                        readonly property var watt: backend.pcStatus.watt

                        title: "Power"
                        known: false
                        value: watt === null || watt === undefined ? "Unknown" : Number(watt).toFixed(1) + " W"
                    }
                    StatusTile {
                        readonly property var rdp: backend.pcStatus.rdp

                        title: "Remote desktop"
                        known: rdp === true || rdp === false
                        good: rdp === true
                        value: rdp === true ? "Ready" : rdp === false ? "Not reachable" : "Unknown"
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 1
                    color: palette.windowText
                    opacity: 0.12
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Item {
                        visible: backend.running
                        Layout.preferredWidth: 24
                        Layout.maximumWidth: 24
                        Layout.preferredHeight: 24

                        BusyIndicator {
                            anchors.fill: parent
                            padding: 0
                            running: backend.running
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: backend.status
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.maximumWidth: 260
                        opacity: 0.7
                        elide: Text.ElideRight
                        text: backend.pcStatus.error
                            ? backend.pcStatus.error
                            : backend.pcStatus.updated ? "Updated " + backend.pcStatus.updated : "Checking..."
                    }
                    Button {
                        text: "Refresh"
                        flat: true
                        onClicked: backend.refreshStatus()
                    }
                    Button {
                        visible: backend.running
                        enabled: !backend.cancelling
                        text: backend.cancelling ? "Cancelling..." : "Cancel"
                        onClicked: backend.cancel()
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
