package com.connecty.app.network.nsd

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.util.Log
import com.connecty.app.models.DiscoveredPeer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.net.InetAddress

class NsdDiscoveryManager(private val context: Context) {
    private val TAG = "ConnectyNSD"
    private val SERVICE_TYPE = "_homesync._tcp."

    private val nsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
    private var multicastLock: WifiManager.MulticastLock? = null

    private val _discoveredPeers = MutableStateFlow<List<DiscoveredPeer>>(emptyList())
    val discoveredPeers: StateFlow<List<DiscoveredPeer>> = _discoveredPeers.asStateFlow()

    private var isDiscovering = false

    private val discoveryListener = object : NsdManager.DiscoveryListener {
        override fun onDiscoveryStarted(regType: String) {
            Log.d(TAG, "Service discovery started: $regType")
            isDiscovering = true
        }

        override fun onServiceFound(service: NsdServiceInfo) {
            Log.d(TAG, "Service found: ${service.serviceName}")
            if (service.serviceType.contains("_homesync")) {
                try {
                    nsdManager.resolveService(service, createResolveListener())
                } catch (e: Exception) {
                    Log.e(TAG, "Resolve failed immediately: ${e.message}")
                }
            }
        }

        override fun onServiceLost(service: NsdServiceInfo) {
            Log.d(TAG, "Service lost: ${service.serviceName}")
            val current = _discoveredPeers.value.toMutableList()
            current.removeAll { it.name == service.serviceName }
            _discoveredPeers.value = current
        }

        override fun onDiscoveryStopped(serviceType: String) {
            Log.d(TAG, "Discovery stopped: $serviceType")
            isDiscovering = false
        }

        override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
            Log.e(TAG, "Discovery start failed: Error code: $errorCode")
            nsdManager.stopServiceDiscovery(this)
            isDiscovering = false
        }

        override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
            Log.e(TAG, "Discovery stop failed: Error code: $errorCode")
            nsdManager.stopServiceDiscovery(this)
            isDiscovering = false
        }
    }

    private fun createResolveListener(): NsdManager.ResolveListener {
        return object : NsdManager.ResolveListener {
            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "Resolve failed: $errorCode")
            }

            override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                val host: InetAddress? = serviceInfo.host
                val port = serviceInfo.port
                val hostAddress = host?.hostAddress ?: return

                Log.d(TAG, "Resolved service: ${serviceInfo.serviceName} at $hostAddress:$port")

                val peer = DiscoveredPeer(
                    name = serviceInfo.serviceName,
                    host = hostAddress,
                    port = port,
                    deviceName = serviceInfo.serviceName.substringBefore("._")
                )

                val current = _discoveredPeers.value.toMutableList()
                current.removeAll { it.name == peer.name }
                current.add(peer)
                _discoveredPeers.value = current
            }
        }
    }

    fun startDiscovery() {
        if (isDiscovering) return

        try {
            // Acquire Multicast lock for mDNS packet reception on Android Wi-Fi
            if (multicastLock == null) {
                multicastLock = wifiManager.createMulticastLock("ConnectyMulticastLock").apply {
                    setReferenceCounted(true)
                    acquire()
                }
            }
            nsdManager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener)
        } catch (e: Exception) {
            Log.e(TAG, "Error starting discovery: ${e.message}")
        }
    }

    fun stopDiscovery() {
        if (!isDiscovering) return
        try {
            nsdManager.stopServiceDiscovery(discoveryListener)
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping discovery: ${e.message}")
        } finally {
            multicastLock?.let {
                if (it.isHeld) it.release()
            }
            multicastLock = null
            isDiscovering = false
        }
    }
}
