import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page

    signal resetRequested()

    readonly property bool dark: Application.styleHints.colorScheme === Qt.Dark
    readonly property color goodColor: dark ? "#6ccb5f" : "#0f7b0f"
    readonly property color badColor: dark ? "#ff99a4" : "#c42b1c"

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 24
        anchors.leftMargin: 16
        anchors.rightMargin: 24
        spacing: 12

        Label {
            text: "Settings"
            font.pixelSize: 28
            font.weight: Font.DemiBold
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Label {
                Layout.fillWidth: true
                elide: Text.ElideRight
                color: backend.notice.error ? page.badColor : palette.windowText
                opacity: backend.notice.error ? 1 : 0.8
                text: backend.notice.text || (backend.dirty ? "Unsaved changes" : "")
            }
            Button {
                text: "Reload"
                onClicked: backend.loadSettings()
            }
            Button {
                text: "Reset to defaults"
                onClicked: page.resetRequested()
            }
            Button {
                text: "Save"
                highlighted: backend.dirty
                onClicked: backend.saveSettings()
            }
        }

        ScrollView {
            id: scroll

            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: scroll.availableWidth - 8
                spacing: 6

                Repeater {
                    model: backend.settingGroups

                    ColumnLayout {
                        id: group

                        required property var modelData

                        Layout.fillWidth: true
                        Layout.topMargin: 8
                        spacing: 6

                        Label {
                            text: group.modelData.title
                            font.weight: Font.DemiBold
                        }

                        Frame {
                            Layout.fillWidth: true

                            ColumnLayout {
                                anchors.fill: parent
                                spacing: 14

                                Repeater {
                                    model: group.modelData.fields

                                    SettingRow {
                                        required property var modelData

                                        Layout.fillWidth: true
                                        field: modelData
                                    }
                                }

                                RowLayout {
                                    readonly property var result: backend.testResults[group.modelData.test]

                                    visible: group.modelData.test !== ""
                                    Layout.fillWidth: true
                                    spacing: 12

                                    Button {
                                        text: group.modelData.testLabel
                                        enabled: !backend.running
                                        onClicked: backend.testSetting(group.modelData.test)
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        text: parent.result ? parent.result.text : "Uses the values above, even before saving."
                                        color: parent.result ? (parent.result.ok ? page.goodColor : page.badColor) : palette.windowText
                                        opacity: parent.result ? 1 : 0.7
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    Layout.preferredHeight: 16
                }
            }
        }
    }
}
