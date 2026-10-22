package com.connecty.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.connecty.app.models.FileItem
import com.connecty.app.models.FolderContentsResponse

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FileBrowserScreen(
    folderData: FolderContentsResponse?,
    isLoading: Boolean,
    onNavigateSubfolder: (subpath: String) -> Unit,
    onNavigateUp: () -> Unit,
    onPlayMedia: (file: FileItem) -> Unit,
    onDownloadFile: (file: FileItem) -> Unit,
    onUploadFile: (uri: Uri, fileName: String) -> Unit,
    onDisconnect: () -> Unit,
    uploadProgress: Int?,
    uploadStatus: String?
) {
    val context = LocalContext.current
    val filePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            val fileName = getFileNameFromUri(context, it) ?: "upload_${System.currentTimeMillis()}"
            onUploadFile(it, fileName)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(folderData?.folder_name ?: "Shared Files", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        Text(
                            "/" + (folderData?.current_path ?: ""),
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    if (folderData?.has_parent == true) {
                        IconButton(onClick = onNavigateUp) {
                            Icon(Icons.Default.ArrowBack, contentDescription = "Up")
                        }
                    }
                },
                actions = {
                    IconButton(onClick = onDisconnect) {
                        Icon(Icons.Default.Logout, contentDescription = "Disconnect")
                    }
                }
            )
        },
        floatingActionButton = {
            if (folderData?.allow_write == true) {
                FloatingActionButton(
                    onClick = { filePickerLauncher.launch("*/*") }
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Upload File")
                }
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (folderData == null || folderData.items.isEmpty()) {
                Column(
                    modifier = Modifier.align(Alignment.Center),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(Icons.Default.FolderOpen, contentDescription = null, modifier = Modifier.size(48.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("This folder is empty", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(folderData.items) { item ->
                        val isVideo = item.mime_type.startsWith("video/")
                        val isAudio = item.mime_type.startsWith("audio/")
                        val isMedia = isVideo || isAudio

                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    if (item.is_dir) {
                                        onNavigateSubfolder(item.relative_path)
                                    } else if (isMedia) {
                                        onPlayMedia(item)
                                    } else {
                                        onDownloadFile(item)
                                    }
                                }
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                val icon = when {
                                    item.is_dir -> Icons.Default.Folder
                                    isVideo -> Icons.Default.Movie
                                    isAudio -> Icons.Default.MusicNote
                                    else -> Icons.Default.InsertDriveFile
                                }

                                Icon(icon, contentDescription = null, modifier = Modifier.size(28.dp))
                                Spacer(modifier = Modifier.width(16.dp))

                                Column(modifier = Modifier.weight(1f)) {
                                    Text(item.name, fontWeight = FontWeight.SemiBold, fontSize = 15.sp, maxLines = 1)
                                    Text(
                                        if (item.is_dir) "Folder" else "${formatFileSize(item.size)}",
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }

                                if (isMedia) {
                                    IconButton(onClick = { onPlayMedia(item) }) {
                                        Icon(Icons.Default.PlayArrow, contentDescription = "Play")
                                    }
                                }
                                if (!item.is_dir) {
                                    IconButton(onClick = { onDownloadFile(item) }) {
                                        Icon(Icons.Default.Download, contentDescription = "Download")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Upload Progress Dialog
            if (uploadProgress != null) {
                AlertDialog(
                    onDismissRequest = {},
                    title = { Text("Uploading to Laptop") },
                    text = {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            LinearProgressIndicator(
                                progress = uploadProgress / 100f,
                                modifier = Modifier.fillMaxWidth()
                            )
                            Text("$uploadProgress% - ${uploadStatus ?: "Chunked Transfer"}", fontSize = 12.sp)
                        }
                    },
                    confirmButton = {}
                )
            }
        }
    }
}

private fun formatFileSize(bytes: Long): String {
    if (bytes <= 0) return "0 B"
    val units = arrayOf("B", "KB", "MB", "GB", "TB")
    val digitGroups = (Math.log10(bytes.toDouble()) / Math.log10(1024.0)).toInt()
    return String.format("%.1f %s", bytes / Math.pow(1024.0, digitGroups.toDouble()), units[digitGroups])
}

private fun getFileNameFromUri(context: android.content.Context, uri: Uri): String? {
    var result: String? = null
    if (uri.scheme == "content") {
        val cursor = context.contentResolver.query(uri, null, null, null, null)
        cursor?.use {
            if (it.moveToFirst()) {
                val index = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                if (index != -1) result = it.getString(index)
            }
        }
    }
    if (result == null) {
        result = uri.path
        val cut = result?.lastIndexOf('/') ?: -1
        if (cut != -1) result = result?.substring(cut + 1)
    }
    return result
}
