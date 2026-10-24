import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: row

    required property var field

    spacing: 24

    IntValidator {
        id: intValidator

        bottom: 1
    }

    DoubleValidator {
        id: floatValidator

        bottom: 0
        decimals: 2
        notation: DoubleValidator.StandardNotation
        locale: "C"
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2

        Label {
            Layout.fillWidth: true
            text: row.field.label
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            text: row.field.description
            opacity: 0.7
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    TextField {
        visible: row.field.kind !== "choice"
        Layout.preferredWidth: 300
        text: backend.values[row.field.key] || ""
        placeholderText: row.field.placeholder
        echoMode: row.field.kind === "secret" ? TextInput.Password : TextInput.Normal
        validator: row.field.kind === "int" ? intValidator : row.field.kind === "float" ? floatValidator : null
        inputMethodHints: row.field.kind === "int" || row.field.kind === "float" ? Qt.ImhFormattedNumbersOnly : Qt.ImhNone
        onTextEdited: backend.setValue(row.field.key, text)

        ToolTip.visible: hovered
        ToolTip.delay: 600
        ToolTip.text: row.field.key
    }

    ComboBox {
        visible: row.field.kind === "choice"
        Layout.preferredWidth: 300
        model: row.field.choices
        currentIndex: Math.max(0, row.field.choices.indexOf(backend.values[row.field.key]))
        onActivated: backend.setValue(row.field.key, currentText)
    }
}
