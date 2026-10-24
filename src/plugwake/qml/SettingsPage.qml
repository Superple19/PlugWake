import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page

    signal resetRequested()

    ScrollView {
        id: scroll

        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            x: 16
            y: 24
            width: scroll.availableWidth - 40
            spacing: 12

            Label {
                text: "Settings"
                font.pixelSize: 28
                font.weight: Font.DemiBold
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
                            spacing: 10

                            Repeater {
                                model: group.modelData.fields

                                RowLayout {
                                    id: row

                                    required property var modelData
                                    readonly property var field: modelData

                                    Layout.fillWidth: true
                                    spacing: 16

                                    Label {
                                        text: row.field.key
                                        Layout.preferredWidth: 230
                                        elide: Text.ElideRight
                                    }

                                    TextField {
                                        visible: row.field.choices.length === 0
                                        Layout.fillWidth: true
                                        text: backend.values[row.field.key] || ""
                                        placeholderText: row.field.placeholder
                                        echoMode: row.field.secret ? TextInput.Password : TextInput.Normal
                                        onTextEdited: backend.setValue(row.field.key, text)
                                    }

                                    ComboBox {
                                        visible: row.field.choices.length > 0
                                        Layout.fillWidth: true
                                        model: row.field.choices
                                        currentIndex: Math.max(0, row.field.choices.indexOf(backend.values[row.field.key]))
                                        onActivated: backend.setValue(row.field.key, currentText)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.topMargin: 8
                Layout.bottomMargin: 24
                spacing: 8

                Button {
                    text: "Save .env"
                    highlighted: true
                    onClicked: backend.saveSettings()
                }
                Button {
                    text: "Reload .env"
                    onClicked: backend.loadSettings()
                }
                Button {
                    text: "Reset Defaults"
                    onClicked: page.resetRequested()
                }
            }
        }
    }
}
