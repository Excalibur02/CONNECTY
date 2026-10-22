package com.connecty.app.models

data class DeviceInfo(
    val device_name: String,
    val device_id: String,
    val device_type: String,
    val protocol_version: String,
    val lan_ip: String,
    val port: Int,
    val capabilities: List<String>,
    val connection_url: String
)

data class PairingRequest(
    val device_id: String,
    val device_name: String,
    val platform: String = "android",
    val pin_code: String,
    val requested_role: String = "full"
)

data class PairingResponse(
    val status: String,
    val device_id: String,
    val device_name: String,
    val role: String,
    val token: String
)

data class SharedFolder(
    val id: String,
    val name: String,
    val allow_write: Boolean,
    val is_active: Boolean
)

data class FoldersResponse(
    val folders: List<SharedFolder>
)

data class FileItem(
    val id: String,
    val name: String,
    val is_dir: Boolean,
    val size: Long,
    val mime_type: String,
    val modified: Double,
    val relative_path: String
)

data class FolderContentsResponse(
    val folder_id: String,
    val folder_name: String,
    val allow_write: Boolean,
    val current_path: String,
    val has_parent: Boolean,
    val parent_id: String?,
    val items: List<FileItem>
)

data class TransferInitRequest(
    val filename: String,
    val total_size: Long,
    val total_chunks: Int,
    val chunk_size: Int,
    val expected_hash: String,
    val target_folder_id: String = "default",
    val target_subpath: String = ""
)

data class TransferInitResponse(
    val transfer_id: String,
    val filename: String,
    val total_size: Long,
    val total_chunks: Int,
    val chunk_size: Int,
    val status: String
)

data class TransferProgressResponse(
    val transfer_id: String,
    val filename: String,
    val total_size: Long,
    val total_chunks: Int,
    val received_chunks: List<Int>,
    val status: String
)

data class TransferCompleteResponse(
    val transfer_id: String,
    val status: String,
    val filename: String,
    val file_id: String,
    val size: Long,
    val sha256: String
)

data class DiscoveredPeer(
    val name: String,
    val host: String,
    val port: Int,
    val deviceName: String
)
