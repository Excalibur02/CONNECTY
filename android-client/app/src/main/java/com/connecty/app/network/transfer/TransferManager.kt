package com.connecty.app.network.transfer

import android.content.Context
import android.net.Uri
import com.connecty.app.models.TransferCompleteResponse
import com.connecty.app.models.TransferInitRequest
import com.connecty.app.network.api.ConnectyApiService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.InputStream
import java.security.MessageDigest
import kotlin.math.ceil

class TransferManager(
    private val context: Context,
    private val api: ConnectyApiService,
    private val token: String
) {
    private val CHUNK_SIZE = 2 * 1024 * 1024 // 2 MiB chunks

    suspend fun uploadFile(
        fileUri: Uri,
        fileName: String,
        targetFolderId: String = "default",
        targetSubpath: String = "",
        onProgress: (percent: Int, currentChunk: Int, totalChunks: Int) -> Unit
    ): Result<TransferCompleteResponse> = withContext(Dispatchers.IO) {
        try {
            val contentResolver = context.contentResolver
            
            // 1. Get file size
            val fileSize = contentResolver.openFileDescriptor(fileUri, "r")?.use {
                it.statSize
            } ?: throw IllegalStateException("Cannot read file size")

            val totalChunks = ceil(fileSize.toDouble() / CHUNK_SIZE).toInt().coerceAtLeast(1)

            // 2. Compute streaming SHA-256
            onProgress(0, 0, totalChunks)
            val sha256Digest = MessageDigest.getInstance("SHA-256")
            val buffer = ByteArray(64 * 1024)
            contentResolver.openInputStream(fileUri)?.use { input ->
                var read: Int
                while (input.read(buffer).also { read = it } != -1) {
                    sha256Digest.update(buffer, 0, read)
                }
            } ?: throw IllegalStateException("Cannot open input stream for hashing")

            val expectedHash = sha256Digest.digest().joinToString("") { "%02x".format(it) }

            // 3. Initiate Transfer
            val initResponse = api.initTransfer(
                token = token,
                request = TransferInitRequest(
                    filename = fileName,
                    total_size = fileSize,
                    total_chunks = totalChunks,
                    chunk_size = CHUNK_SIZE,
                    expected_hash = expectedHash,
                    target_folder_id = targetFolderId,
                    target_subpath = targetSubpath
                )
            )

            val transferId = initResponse.transfer_id

            // 4. Check for already received chunks if resuming
            val progress = api.getTransferProgress(token, transferId)
            val received = progress.received_chunks.toSet()

            // 5. Upload Chunks
            contentResolver.openInputStream(fileUri)?.use { input ->
                var currentChunk = 0
                val chunkBuffer = ByteArray(CHUNK_SIZE)

                while (currentChunk < totalChunks) {
                    var chunkBytesRead = 0
                    while (chunkBytesRead < CHUNK_SIZE) {
                        val bytesToRead = CHUNK_SIZE - chunkBytesRead
                        val n = input.read(chunkBuffer, chunkBytesRead, bytesToRead)
                        if (n == -1) break
                        chunkBytesRead += n
                    }

                    if (chunkBytesRead > 0) {
                        if (!received.contains(currentChunk)) {
                            val chunkData = if (chunkBytesRead == CHUNK_SIZE) {
                                chunkBuffer
                            } else {
                                chunkBuffer.copyOf(chunkBytesRead)
                            }

                            val body = chunkData.toRequestBody("application/octet-stream".toMediaTypeOrNull())
                            val chunkRes = api.uploadChunk(token, transferId, currentChunk, body)
                            if (!chunkRes.isSuccessful) {
                                throw IllegalStateException("Failed to upload chunk $currentChunk: ${chunkRes.code()}")
                            }
                        }

                        val pct = (((currentChunk + 1).toDouble() / totalChunks) * 100).toInt()
                        onProgress(pct, currentChunk + 1, totalChunks)
                    }
                    currentChunk++
                }
            } ?: throw IllegalStateException("Failed to open stream for upload")

            // 6. Finalize Transfer and verify checksum on server
            val completeRes = api.completeTransfer(token, transferId)
            Result.success(completeRes)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
