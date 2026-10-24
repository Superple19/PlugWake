import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page

    signal resetRequested()

    function t(text) {
        return backend.strings[text] || text
    }

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
            text: page.t("Settings")
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
                text: backend.notice.text || (backend.dirty ? page.t("Unsaved changes") : "")
            }
            Button {
                text: page.t("Reload")
                onClicked: backend.loadSettings()
            }
            Button {
                text: page.t("Reset to defaults")
                onClicked: page.resetRequested()
            }
            Button {
                text: page.t("Save")
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

                Label {
                    Layout.topMargin: 8
                    text: page.t("App")
                    font.weight: Font.DemiBold
                }

                Frame {
                    Layout.fillWidth: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 24

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Label {
                                    Layout.fillWidth: true
                                    text: page.t("Language")
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: page.t("Applies right away. Logs stay in English.")
                                    opacity: 0.7
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }

                            ComboBox {
                                readonly property var codes: ["system", "en", "ko"]

                                Layout.preferredWidth: 300
                                model: [page.t("Use system language"), "English", "한국어"]
                                currentIndex: Math.max(0, codes.indexOf(backend.language))
                                onActivated: index => backend.setLanguage(codes[index])
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 24

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Label {
                                    Layout.fillWidth: true
                                    text: page.t("Status refresh")
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: page.t("How often Home checks the plug and RDP. Refresh still works when this is off.")
                                    opacity: 0.7
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }
                            }

                            ComboBox {
                                Layout.preferredWidth: 300
                                model: backend.refreshChoices.map(
                                    seconds => seconds === 0 ? page.t("Off") : page.t("Every %1 s").arg(seconds))
                                currentIndex: Math.max(0, backend.refreshChoices.indexOf(backend.refreshSeconds))
                                onActivated: index => backend.setRefreshSeconds(backend.refreshChoices[index])
                            }
                        }
                    }
                }

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
                                        text: parent.result
                                            ? page.t(parent.result.text)
                                            : page.t("Uses the values above, even before saving.")
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
