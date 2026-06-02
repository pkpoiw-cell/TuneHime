; 音姬 TuneHime - NSIS 安装脚本
; 集成 VB-CABLE 虚拟声卡

!macro customInit
  ; 检查是否已安装 VB-CABLE
  ReadRegStr $0 HKLM "SOFTWARE\VB-Audio\CABLE" "InstallDir"
  ${If} $0 != ""
    StrCpy $VB_CABLE_INSTALLED "1"
  ${Else}
    StrCpy $VB_CABLE_INSTALLED "0"
  ${EndIf}
!macroend

!macro customInstall
  ; 安装 VB-CABLE（如果未安装）
  ${If} $VB_CABLE_INSTALLED == "0"
    MessageBox MB_YESNO "音姬需要安装 VB-CABLE 虚拟声卡才能正常使用。$\n$\n是否现在安装？" IDYES install_vbcable IDNO skip_vbcable

    install_vbcable:
      ; 显示安装说明
      MessageBox MB_OK "即将安装 VB-CABLE 虚拟声卡。$\n$\n安装过程中可能会弹出驱动安装确认框，请点击'安装'按钮。$\n$\n安装完成后，系统可能需要重启。"

      ; 解压 VB-CABLE 安装文件
      SetOutPath "$TEMP\vb-cable"
      File /r "${BUILD_RESOURCES_DIR}\vb-cable\*.*"

      ; 运行 VB-CABLE 安装程序
      ExecWait '"$TEMP\vb-cable\VBCABLE_Setup_x64.exe"'

      ; 清理临时文件
      RMDir /r "$TEMP\vb-cable"

      MessageBox MB_OK "VB-CABLE 安装完成！$\n$\n如果系统提示需要重启，请在安装完成后重启电脑。"
      Goto done_vbcable

    skip_vbcable:
      MessageBox MB_OK "您选择跳过安装 VB-CABLE。$\n$\n请注意：没有 VB-CABLE，音姬将无法连接到直播软件。$\n$\n您可以稍后手动安装。"

    done_vbcable:
  ${EndIf}

  ; 创建开始菜单快捷方式
  CreateDirectory "$SMPROGRAMS\音姬 TuneHime"
  CreateShortCut "$SMPROGRAMS\音姬 TuneHime\音姬 TuneHime.lnk" "$INSTDIR\音姬 TuneHime.exe"
  CreateShortCut "$SMPROGRAMS\音姬 TuneHime\卸载音姬.lnk" "$INSTDIR\Uninstall 音姬 TuneHime.exe"

  ; 创建桌面快捷方式
  CreateShortCut "$DESKTOP\音姬 TuneHime.lnk" "$INSTDIR\音姬 TuneHime.exe"
!macroend

!macro customUnInstall
  ; 删除快捷方式
  Delete "$DESKTOP\音姬 TuneHime.lnk"
  RMDir /r "$SMPROGRAMS\音姬 TuneHime"

  ; 询问是否卸载 VB-CABLE
  MessageBox MB_YESNO "是否同时卸载 VB-CABLE 虚拟声卡？$\n$\n注意：如果其他程序也在使用 VB-CABLE，请选择'否'。" IDYES uninstall_vbcable IDNO skip_uninstall_vbcable

  uninstall_vbcable:
    ReadRegStr $0 HKLM "SOFTWARE\VB-Audio\CABLE" "InstallDir"
    ${If} $0 != ""
      ExecWait '"$0\VBCABLE_Setup_x64.exe" -u'
      MessageBox MB_OK "VB-CABLE 已卸载。"
    ${EndIf}
    Goto done_uninstall

  skip_uninstall_vbcable:
    Goto done_uninstall

  done_uninstall:
!macroend

; 变量
Var VB_CABLE_INSTALLED
