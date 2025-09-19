
##############################
##                          ##
## mynameismatt :imhelping: ##
##                          ##
##############################

# Load functions, environment variables, and script variables
Import-Module "/users/matthew/Documents/Scripting/Modules/Matthew.psm1"
$ftphost = "matthewrstreeter.com"
$localPath = "/Users/matthew/Library/Containers/com.ootpdevelopments.ootp25macqlm/Data/Application Support/Out of the Park Developments/OOTP Baseball 25/saved_games/NPBL.lg/import_export/mysql/"
$remotePath = "/home/mstreeter06/matthewrstreeter.com/ootp/npbl/sql/"
$FileFilter = "*.mysql.sql"
$commishBotNPBL = 'xoxb-'
$slackToken = $commishBotNPBL #OAuth Token
$customUsername = "StatsLab Bot" #Custom Bot Username
$channelId = 'C09KSJH9U' #commish_news - #Channel ID or Channel Name
$message = "<https://www.matthewrstreeter.com/ootp/npbl/statslab/login.php|NPBL StatsLab> has been updated" #Message text

# Import credentials from the XML file
$credential = Import-CliXml -Path "./mstreeter06.xml"

# Extract the username and password
$username = $credential.UserName
$password = $credential.GetNetworkCredential().Password

# Connect to $ftphost FTP and then list remote files and save the output to a variable
$lftpCommand = @"
lftp -c "open sftp://$($username):$($password)@$($ftphost); cls -l --time-style=+\"%Y-%m-%d %H:%M:%S\" $remotePath"
"@
$remoteFilesOutput = bash -c "$lftpCommand"

# Parse the LFTP output to extract filenames and timestamps
$remoteFiles = @()
foreach ($line in $remoteFilesOutput -split "`n") {
    if ($line -match "(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(.+)") {
        # Extract the full remote path and trim it to just the file name
        $fullPath = $matches[2]
        $fileName = (Split-Path -Path $fullPath -Leaf)  # Extract only the file name

        $remoteFiles += @{
            Name = $fileName
            LastWriteTime = [datetime]::ParseExact($matches[1], 'yyyy-MM-dd HH:mm:ss', $null)
        }
    }
}

# Get local files
$localFiles = Get-ChildItem -Path $localPath -Filter $FileFilter

# Compare local and remote files, ignoring milliseconds
foreach ($localFile in $localFiles) {
    $remoteFile = $remoteFiles | Where-Object { $_.Name -eq $localFile.Name }
    if ($remoteFile) {
        # Truncate milliseconds by parsing to seconds
        $remoteLastWriteTime = [datetime]::ParseExact($remoteFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), 'yyyy-MM-dd HH:mm:ss', $null)
        $localLastWriteTime = [datetime]::ParseExact($localFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), 'yyyy-MM-dd HH:mm:ss', $null)

        if ($remoteLastWriteTime -lt $localLastWriteTime) {
            Write-Host "Local file $($localFile.Name) is newer than the remote version."
        } elseif ($remoteLastWriteTime -eq $localLastWriteTime) {
            Write-Host "Remote file $($localFile.Name) is up to date."
        }
    } else {
        Write-Host "Local file $($localFile.Name) is not found on the remote server."
    }
}

# Construct the LFTP command with multiple uploads in one session
$lftpCommands = "open sftp://$($username):$($password)@$($ftphost); cd $remotePath;"

foreach ($localFile in $localFiles) {
    $remoteFile = $remoteFiles | Where-Object { $_.Name -eq $localFile.Name }
    if ($remoteFile) {
        $remoteLastWriteTime = [datetime]::ParseExact($remoteFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), 'yyyy-MM-dd HH:mm:ss', $null)
        $localLastWriteTime = [datetime]::ParseExact($localFile.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), 'yyyy-MM-dd HH:mm:ss', $null)

        if ($remoteLastWriteTime -lt $localLastWriteTime) {
            Write-Host "Queuing upload for $($localFile.Name) as it is newer than the remote version."
            $lftpCommands += " put '$($localFile.FullName)';"
        }
    } else {
        Write-Host "Queuing upload for $($localFile.Name) as it is not found on the remote server."
        $lftpCommands += " put '$($localFile.FullName)';"
    }
}

# Only execute if there are files to upload
if ($lftpCommands -match "put") {
    # Wrap the LFTP commands with the closing command
    $lftpCommand = @"
lftp -c "$lftpCommands"
"@
    # Execute the full set of upload commands in one LFTP session
    bash -c "$lftpCommand"
} else {
    Write-Host "No files to upload."
}

# Run function to update StatsLab
Update-StatsLabNPBL

# Send Slack message to commish-news about StatsLab being updated

Send-SlackMessage -slackToken $slackToken -channelId $channelId -customUsername $customUsername -message $message -iconEmoji ":baseball-field:"
