Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strAppDir = FSO.GetParentFolderName(WScript.ScriptFullName)
strUser = WshShell.ExpandEnvironmentStrings("%USERNAME%")

strPython = "C:\Users\" & strUser & "\.local_translator_venv\Scripts\pythonw.exe"
If Not FSO.FileExists(strPython) Then
    strPython = "C:\Users\" & strUser & "\.local_translator_venv\Scripts\python.exe"
End If

' 0 = vbHide (Completamente invisible, sin consola CMD), False = No esperar
strCommand = Chr(34) & strPython & Chr(34) & " " & Chr(34) & strAppDir & "\main.py" & Chr(34)
WshShell.Run strCommand, 0, False

Set WshShell = Nothing
Set FSO = Nothing
