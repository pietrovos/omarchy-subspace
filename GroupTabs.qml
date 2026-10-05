import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "pietrovos.subspace"

  property var members: []
  property int activeIndex: -1
  property string subspaceName: ""
  readonly property real leadingGap: Style.spaceReal(14)
  readonly property string helperPath: Qt.resolvedUrl("scripts/subspace.py").toString().replace(/^file:\/\//, "")
  readonly property string stateDir: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/omarchy/subspace"
  readonly property real labelGap: subspaceName !== "" ? Style.spaceReal(-1) : 0

  function refresh() {
    if (!groupProbe.running) groupProbe.running = true
  }

  function updateGroup(output) {
    try {
      var active = JSON.parse(output)
      if (!active.address) throw new Error("No focused window")
      subspaceName = active.subspaceName || ""
      members = active.grouped || []
      activeIndex = members.indexOf(active.address)
    } catch (error) {
      members = []
      activeIndex = -1
      subspaceName = ""
    }
  }

  function focusMember(index) {
    if (!root.bar) return
    activeIndex = index - 1
    root.bar.run("hyprctl dispatch " + Util.shellQuote("hl.dsp.group.active({ index = " + index + " })"))
  }

  function renameGroup() {
    if (!renameProcess.running) renameProcess.running = true
  }

  visible: members.length > 0 && !vertical
  implicitWidth: visible ? leadingGap + tabGroup.implicitWidth + labelGap + labelBox.implicitWidth : 0
  implicitHeight: root.barSize

  Process {
    id: groupProbe
    command: ["python3", decodeURIComponent(root.helperPath)]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.updateGroup(text)
    }
    onExited: function(exitCode) {
      if (exitCode !== 0) root.updateGroup("{}")
    }
  }

  Process {
    id: renameProcess
    command: ["python3", decodeURIComponent(root.helperPath), "rename"]
    onExited: root.refresh()
  }

  Timer {
    interval: 1000
    repeat: true
    running: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (["activewindow", "activewindowv2", "closewindow", "movewindowv2", "openwindow", "changeworkspaceid", "togglegroup", "moveintogroup", "moveoutofgroup"].indexOf(event.name) !== -1) root.refresh()
    }
  }

  FileView {
    path: root.stateDir + "/groups.json"
    watchChanges: true
    printErrors: false
    onFileChanged: {
      reload()
      root.refresh()
    }
  }

  Rectangle {
    x: tabGroup.x
    anchors.verticalCenter: parent.verticalCenter
    width: tabGroup.width + (labelBox.visible ? root.labelGap + labelBox.width : 0)
    height: tabGroup.height
    color: "transparent"
    radius: Math.min(Style.cornerRadius, height / 2)
    border.width: 1
    border.color: root.bar ? root.bar.barForeground : Color.foreground
    opacity: 0.5
  }

  Item {
    id: tabGroup
    x: root.leadingGap
    anchors.verticalCenter: parent.verticalCenter
    implicitWidth: grid.implicitWidth + Style.space(2)
    implicitHeight: root.barSize - Style.space(2)
    width: implicitWidth
    height: implicitHeight

    Rectangle {
      anchors.fill: parent
      color: root.bar ? root.bar.barForeground : Color.foreground
      radius: Math.min(Style.cornerRadius, height / 2)
      opacity: 0.12
    }

    GridLayout {
      id: grid
      anchors.centerIn: parent
      columns: Math.max(1, root.members.length)
      columnSpacing: Style.space(1)

      Repeater {
        model: root.members
        WidgetButton {
          required property int index
          readonly property bool focused: index === root.activeIndex
          bar: root.bar
          text: focused ? "\uDB85\uDCFB" : (index === 9 ? "0" : String(index + 1))
          tooltipText: "Window " + (index + 1) + " · Right-click to name this subspace"
          opacity: focused ? 1 : 0.55
          horizontalMargin: 6
          verticalPadding: 6
          fixedWidth: Style.space(20)
          fixedHeight: tabGroup.height
          onPressed: function(button) {
            if (button === Qt.RightButton) root.renameGroup()
            else if (button === Qt.LeftButton) root.focusMember(index + 1)
          }
        }
      }
    }
  }

  Item {
    id: labelBox
    visible: root.subspaceName !== ""
    x: tabGroup.x + tabGroup.width + root.labelGap
    anchors.verticalCenter: parent.verticalCenter
    implicitWidth: subspaceLabel.implicitWidth + Style.space(8)
    implicitHeight: root.barSize - Style.space(2)
    width: implicitWidth
    height: implicitHeight

    Rectangle {
      anchors.fill: parent
      color: root.bar ? root.bar.barForeground : Color.foreground
      radius: Math.min(Style.cornerRadius, height / 2)
      opacity: 0.12
    }

    Text {
      id: subspaceLabel
      anchors.verticalCenter: parent.verticalCenter
      x: Style.space(4)
      text: root.subspaceName
      textFormat: Text.PlainText
      color: root.bar ? root.bar.barForeground : Color.foreground
      opacity: 0.85
      font.family: root.bar ? root.bar.fontFamily : Style.font.family
      font.pixelSize: Style.font.body
    }

    MouseArea {
      anchors.fill: parent
      cursorShape: Qt.PointingHandCursor
      acceptedButtons: Qt.LeftButton | Qt.RightButton
      onClicked: root.renameGroup()
    }
  }
}
