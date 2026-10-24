import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page

    signal actionRequested(string actionId)

    function t(text) {
        return backend.strings[text] || text
    }

    readonly property color dangerColor: Application.styleHints.colorScheme === Qt.Dark ? "#ff99a4" : "#c42b1c"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        anchors.leftMargin: 16
        spacing: 12

        Label {
            text: page.t("Home")
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
                        readonly property var watt: backend.pcStatus.watt
                        readonly property var pcRunning: backend.pcStatus.pc_running
                        readonly property bool hasWatt: watt !== null && watt !== undefined

                        title: page.t("Smart plug")
                        // Warn when power reaches the plug but the PC is off or asleep.
                        tone: plug === "off" ? "off"
                            : plug !== "on" ? ""
                            : pcRunning === true ? "good"
                            : pcRunning === false ? "warn"
                            : "off"
                        value: plug === "off" ? page.t("Off")
                            : plug !== "on" ? page.t("Unknown")
                            : !hasWatt ? page.t("On")
                            : pcRunning === false ? page.t("On (%1 W · PC off)").arg(Number(watt).toFixed(1))
                            : page.t("On (%1 W)").arg(Number(watt).toFixed(1))
                    }
                    StatusTile {
                        readonly property var rdp: backend.pcStatus.rdp

                        title: page.t("Remote desktop")
                        // Warn when the PC draws running power but RDP does not answer.
                        tone: rdp === true ? "good"
                            : rdp !== false ? ""
                            : backend.pcStatus.pc_running === true ? "warn"
                            : "off"
                        value: page.t(rdp === true ? "Ready" : rdp === false ? "Not reachable" : "Unknown")
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
                            : backend.pcStatus.updated
                                ? page.t("Updated %1").arg(backend.pcStatus.updated)
                                : page.t("Checking...")
                    }
                    Button {
                        text: page.t("Refresh")
                        flat: true
                        onClicked: backend.refreshStatus()
                    }
                    Button {
                        visible: backend.running
                        enabled: !backend.cancelling
                        text: page.t(backend.cancelling ? "Cancelling..." : "Cancel")
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
                    text: page.t("Power controls")
                    font.weight: Font.DemiBold
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        Layout.fillWidth: true
                        text: page.t("Remote On")
                        highlighted: true
                        enabled: !backend.running
                        onClicked: page.actionRequested("on")
                    }
                    Button {
                        Layout.fillWidth: true
                        text: page.t("Remote Off")
                        enabled: !backend.running
                        onClicked: page.actionRequested("off")
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        text: page.t("Soft Reboot")
                        enabled: !backend.running
                        onClicked: page.actionRequested("reboot")
                    }
                    Button {
                        text: page.t("Hard Reboot")
                        enabled: !backend.running
                        palette.active.buttonText: page.dangerColor
                        palette.inactive.buttonText: page.dangerColor
                        onClicked: page.actionRequested("hard-reboot")
                    }
                    Item {
                        Layout.fillWidth: true
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
                        text: page.t("Log")
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                    }
                    Button {
                        text: page.t("Clear")
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
