package com.connecty.app

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import com.connecty.app.models.DiscoveredPeer
import com.connecty.app.models.FileItem
import com.connecty.app.models.FolderContentsResponse
import com.connecty.app.models.PairingRequest
import com.connecty.app.network.api.ConnectyApiClient
import com.connecty.app.network.api.ConnectyApiService
import com.connecty.app.network.nsd.NsdDiscoveryManager
import com.connecty.app.network.transfer.TransferManager
import com.connecty.app.ui.screens.DiscoveryScreen
import com.connecty.app.ui.screens.FileBrowserScreen
import com.connecty.app.ui.screens.PlayerScreen
import kotlinx.coroutines.launch
import java.util.*

class MainActivity : ComponentActivity() {
    private lateinit var nsdManager: NsdDiscoveryManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        nsdManager = NsdDiscoveryManager(this)

        setContent {
            val scope = rememberCoroutineScope()
            val peers by nsdManager.discoveredPeers.collectAsState()

            var currentScreen by remember { mutableStateOf<Screen>(Screen.Discovery) }
            var apiService by remember { mutableStateOf<ConnectyApiService?>(null) }
            var currentToken by remember { mutableStateOf("") }
            var currentBaseUrl by remember { mutableStateOf("") }
            
            var folderData by remember { mutableStateOf<FolderContentsResponse?>(null) }
            var isLoading by remember { mutableStateOf(false) }
            var isConnecting by remember { mutableStateOf(false) }
            var errorMessage by remember { mutableStateOf<String?>(null) }

            var uploadProgress by remember { mutableStateOf<Int?>(null) }
            var uploadStatus by remember { mutableStateOf<String?>(null) }

            var playingMediaUrl by remember { mutableStateOf("") }
            var playingMediaTitle by remember { mutableStateOf("") }

            LaunchedEffect(Unit) {
                nsdManager.startDiscovery()
            }

            fun loadFolder(folderId: String = "default", subpath: String = "") {
                val api = apiService ?: return
                scope.launch {
                    isLoading = true
                    try {
                        val res = api.browseFiles(currentToken, folderId, subpath)
                        folderData = res
                    } catch (e: Exception) {
                        Toast.makeText(this@MainActivity, "Failed: ${e.message}", Toast.LENGTH_SHORT).show()
                    } finally {
                        isLoading = false
                    }
                }
            }

            when (currentScreen) {
                Screen.Discovery -> {
                    DiscoveryScreen(
                        discoveredPeers = peers,
                        onRefreshDiscovery = {
                            nsdManager.stopDiscovery()
                            nsdManager.startDiscovery()
                        },
                        onConnectToPeer = { host, port, pin ->
                            scope.launch {
                                isConnecting = true
                                errorMessage = null
                                try {
                                    val baseUrl = "http://$host:$port"
                                    val api = ConnectyApiClient.create(baseUrl)
                                    val pairRes = api.pairDevice(
                                        PairingRequest(
                                            device_id = UUID.randomUUID().toString(),
                                            device_name = "Android " + android.os.Build.MODEL,
                                            pin_code = pin,
                                            requested_role = "full"
                                        )
                                    )
                                    apiService = api
                                    currentToken = pairRes.token
                                    currentBaseUrl = baseUrl
                                    currentScreen = Screen.Browser
                                    loadFolder("default", "")
                                } catch (e: Exception) {
                                    errorMessage = "Pairing failed: ${e.message}"
                                } finally {
                                    isConnecting = false
                                }
                            }
                        },
                        isConnecting = isConnecting,
                        errorMessage = errorMessage
                    )
                }

                Screen.Browser -> {
                    FileBrowserScreen(
                        folderData = folderData,
                        isLoading = isLoading,
                        onNavigateSubfolder = { subpath ->
                            loadFolder(folderData?.folder_id ?: "default", subpath)
                        },
                        onNavigateUp = {
                            val parts = (folderData?.current_path ?: "").split("/").filter { it.isNotEmpty() }
                            val parentSubpath = parts.dropLast(1).joinToString("/")
                            loadFolder(folderData?.folder_id ?: "default", parentSubpath)
                        },
                        onPlayMedia = { file ->
                            playingMediaTitle = file.name
                            playingMediaUrl = "$currentBaseUrl/api/v1/files/${file.id}?token=$currentToken"
                            currentScreen = Screen.Player
                        },
                        onDownloadFile = { file ->
                            val dlUrl = "$currentBaseUrl/api/v1/files/${file.id}?download=true&token=$currentToken"
                            val browserIntent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(dlUrl))
                            startActivity(browserIntent)
                        },
                        onUploadFile = { uri, fileName ->
                            val api = apiService ?: return@FileBrowserScreen
                            scope.launch {
                                val transferManager = TransferManager(this@MainActivity, api, currentToken)
                                uploadStatus = "Uploading $fileName..."
                                uploadProgress = 0
                                val result = transferManager.uploadFile(
                                    fileUri = uri,
                                    fileName = fileName,
                                    targetFolderId = folderData?.folder_id ?: "default",
                                    targetSubpath = folderData?.current_path ?: ""
                                ) { pct, curChunk, totalChunks ->
                                    uploadProgress = pct
                                    uploadStatus = "Chunk $curChunk of $totalChunks ($pct%)"
                                }

                                uploadProgress = null
                                uploadStatus = null

                                if (result.isSuccess) {
                                    Toast.makeText(this@MainActivity, "Upload verified & complete!", Toast.LENGTH_LONG).show()
                                    loadFolder(folderData?.folder_id ?: "default", folderData?.current_path ?: "")
                                } else {
                                    Toast.makeText(this@MainActivity, "Upload failed: ${result.exceptionOrNull()?.message}", Toast.LENGTH_LONG).show()
                                }
                            }
                        },
                        onDisconnect = {
                            apiService = null
                            currentToken = ""
                            currentScreen = Screen.Discovery
                        },
                        uploadProgress = uploadProgress,
                        uploadStatus = uploadStatus
                    )
                }

                Screen.Player -> {
                    PlayerScreen(
                        mediaUrl = playingMediaUrl,
                        title = playingMediaTitle,
                        onBack = { currentScreen = Screen.Browser }
                    )
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        nsdManager.stopDiscovery()
    }
}

sealed class Screen {
    object Discovery : Screen()
    object Browser : Screen()
    object Player : Screen()
}
