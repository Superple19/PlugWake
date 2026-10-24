import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window

    property bool micaActive: micaRequested
    property int page: 0
    property var pendingConfirm: null

    width: 900
    height: 620
    minimumWidth: 720
    minimumHeight: 480
    visible: true
    title: "PlugWake"
    color: micaActive ? "transparent" : palette.window

    function confirm(title, text, onYes) {
        confirmDialog.title = title
        confirmLabel.text = text
        pendingConfirm = onYes
        confirmDialog.open()
    }

    function requestAction(actionId) {
        const text = backend.confirmText(actionId)
        if (text === "")
            backend.run(actionId)
        else
            confirm(backend.actionLabel(actionId), text, () => backend.run(actionId))
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.preferredWidth: 220
            Layout.maximumWidth: 220
            Layout.fillWidth: false
            Layout.fillHeight: true
            Layout.margins: 8
            spacing: 4

            RowLayout {
                Layout.leftMargin: 12
                Layout.topMargin: 8
                Layout.bottomMargin: 12
                spacing: 10

                Image {
                    source: appIconUrl
                    sourceSize.width: 24
                    sourceSize.height: 24
                }
                Label {
                    text: "PlugWake"
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }
            }

            Repeater {
                model: ["Home", "Settings"]

                ItemDelegate {
                    required property string modelData
                    required property int index

                    Layout.fillWidth: true
                    text: modelData
                    highlighted: window.page === index
                    onClicked: window.page = index
                }
            }

            Item {
                Layout.fillHeight: true
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.page

            HomePage {
                onActionRequested: actionId => window.requestAction(actionId)
            }

            SettingsPage {
                onResetRequested: window.confirm(
                    "Reset Defaults",
                    "Reset settings fields to example defaults? This will not save .env yet.",
                    () => backend.resetDefaults())
            }
        }
    }

    Dialog {
        id: confirmDialog

        anchors.centerIn: Overlay.overlay
        width: Math.min(440, window.width - 48)
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: {
            if (window.pendingConfirm)
                window.pendingConfirm()
            window.pendingConfirm = null
        }
        onRejected: window.pendingConfirm = null

        Label {
            id: confirmLabel

            width: parent.width
            wrapMode: Text.WordWrap
        }
    }

    Dialog {
        id: passwordDialog

        property string target: ""
        property bool answered: false

        anchors.centerIn: Overlay.overlay
        width: Math.min(440, window.width - 48)
        modal: true
        title: "Password"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onOpened: {
            answered = false
            passwordField.clear()
            passwordField.forceActiveFocus()
        }
        onAccepted: {
            answered = true
            backend.providePassword(passwordField.text, true)
        }
        onClosed: {
            if (!answered)
                backend.providePassword("", false)
        }

        ColumnLayout {
            width: parent.width
            spacing: 8

            Label {
                text: "Password for " + passwordDialog.target
                Layout.fillWidth: true
                wrapMode: Text.WrapAnywhere
            }
            TextField {
                id: passwordField

                Layout.fillWidth: true
                echoMode: TextInput.Password
                onAccepted: passwordDialog.accept()
            }
        }
    }

    Connections {
        target: backend

        function onPasswordRequested(target) {
            passwordDialog.target = target
            passwordDialog.open()
        }
    }
}
