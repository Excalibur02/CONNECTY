package com.connecty.app.network.api

import com.connecty.app.models.*
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.ResponseBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface ConnectyApiService {
    @GET("/api/v1/device")
    suspend fun getDevice(): DeviceInfo

    @POST("/api/v1/pairing/request")
    suspend fun pairDevice(@Body request: PairingRequest): PairingResponse

    @GET("/api/v1/folders")
    suspend fun listFolders(@Header("X-Device-Token") token: String): FoldersResponse

    @GET("/api/v1/files")
    suspend fun browseFiles(
        @Header("X-Device-Token") token: String,
        @Query("folder") folder: String,
        @Query("subpath") subpath: String = ""
    ): FolderContentsResponse

    @Streaming
    @GET("/api/v1/files/{file_id}")
    suspend fun downloadFile(
        @Header("X-Device-Token") token: String,
        @Path("file_id") fileId: String,
        @Query("download") download: Boolean = true
    ): Response<ResponseBody>

    @POST("/api/v1/transfers")
    suspend fun initTransfer(
        @Header("X-Device-Token") token: String,
        @Body request: TransferInitRequest
    ): TransferInitResponse

    @PUT("/api/v1/transfers/{transfer_id}/chunks/{chunk_index}")
    suspend fun uploadChunk(
        @Header("X-Device-Token") token: String,
        @Path("transfer_id") transferId: String,
        @Path("chunk_index") chunkIndex: Int,
        @Body body: RequestBody
    ): Response<Unit>

    @GET("/api/v1/transfers/{transfer_id}")
    suspend fun getTransferProgress(
        @Header("X-Device-Token") token: String,
        @Path("transfer_id") transferId: String
    ): TransferProgressResponse

    @POST("/api/v1/transfers/{transfer_id}/complete")
    suspend fun completeTransfer(
        @Header("X-Device-Token") token: String,
        @Path("transfer_id") transferId: String
    ): TransferCompleteResponse
}

object ConnectyApiClient {
    fun create(baseUrl: String): ConnectyApiService {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        val okHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()

        val normalizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

        return Retrofit.Builder()
            .baseUrl(normalizedUrl)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ConnectyApiService::class.java)
    }
}
