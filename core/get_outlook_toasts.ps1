Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    return $netTask.Result
}

try {
    [Windows.UI.Notifications.Management.UserNotificationListener, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $listener = [Windows.UI.Notifications.Management.UserNotificationListener]::Current
    $status = Await ($listener.RequestAccessAsync()) ([Windows.UI.Notifications.Management.UserNotificationListenerAccessStatus])
    
    if ($status -ne 'Allowed') {
        Write-Output "[]"
        exit 0
    }

    $toasts = Await ($listener.GetNotificationsAsync([Windows.UI.Notifications.NotificationKinds]::Toast)) ([System.Collections.Generic.IReadOnlyList[Windows.UI.Notifications.UserNotification]])
    $results = @()
    foreach ($n in $toasts) {
        $appName = $n.AppInfo.DisplayInfo.DisplayName
        if ($appName -match 'Outlook|olk|Mail') {
            $binding = $n.Notification.Visual.GetBinding([Windows.UI.Notifications.KnownNotificationBindings]::ToastGeneric)
            $texts = @()
            if ($binding) {
                foreach ($t in $binding.GetTextElements()) {
                    if ($t.Text) { $texts += $t.Text.Trim() }
                }
            }
            $sender = if ($texts.Count -gt 0) { $texts[0] } else { "Unknown Sender" }
            $subject = if ($texts.Count -gt 1) { $texts[1] } else { "" }
            $preview = if ($texts.Count -gt 2) { $texts[2..($texts.Count - 1)] -join " " } else { "" }
            
            $results += [PSCustomObject]@{
                id = $n.Id
                app = $appName
                created = $n.CreationTime.ToString("o")
                sender = $sender
                subject = $subject
                preview = $preview
            }
        }
    }
    $results | ConvertTo-Json -Compress
} catch {
    Write-Output "[]"
}
