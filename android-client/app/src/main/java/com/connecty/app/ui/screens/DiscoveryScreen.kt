package com.connecty.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.connecty.app.models.DiscoveredPeer

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DiscoveryScreen(
    discoveredPeers: List<DiscoveredPeer>,
    onRefreshDiscovery: () -> Unit,
    onConnectToPeer: (host: String, port: Int, pin: String) -> Unit,
    isConnecting: Boolean,
    errorMessage: String?
) {
    var manualHost by remember { mutableStateOf("") }
    var manualPort by remember { mutableStateOf("8000") }
    var pinCode by remember { mutableStateOf("") }
    var selectedPeer by remember { mutableStateOf<DiscoveredPeer?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("CONNECTY - Connect to Laptop") },
                actions = {
                    IconButton(onClick = onRefreshDiscovery) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                "Nearby Laptop Shares",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )

            if (discoveredPeers.isEmpty()) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(Icons.Default.Wifi, contentDescription = null, modifier = Modifier.size(36.dp))
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Searching for laptops on local Wi-Fi...", fontSize = 14.sp)
                        Text("Ensure both devices are on the same Wi-Fi router.", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f, fill = false),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(discoveredPeers) { peer ->
                        val isSelected = selectedPeer == peer
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    selectedPeer = peer
                                    manualHost = peer.host
                                    manualPort = peer.port.toString()
                                },
                            colors = CardDefaults.cardColors(
                                containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface
                            ),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.Computer, contentDescription = null, modifier = Modifier.size(32.dp))
                                Spacer(modifier = Modifier.width(16.dp))
                                Column {
                                    Text(peer.deviceName, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                    Text("${peer.host}:${peer.port}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
            }

            Divider()

            Text(
                "Connection Details",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = manualHost,
                    onValueChange = { manualHost = it },
                    label = { Text("Laptop IP (e.g. 192.168.1.6)") },
                    modifier = Modifier.weight(2f)
                )
                OutlinedTextField(
                    value = manualPort,
                    onValueChange = { manualPort = it },
                    label = { Text("Port") },
                    modifier = Modifier.weight(1f)
                )
            }

            OutlinedTextField(
                value = pinCode,
                onValueChange = { if (it.length <= 6) pinCode = it },
                label = { Text("6-Digit Pairing PIN") },
                placeholder = { Text("Check laptop screen") },
                modifier = Modifier.fillMaxWidth()
            )

            if (errorMessage != null) {
                Text(errorMessage, color = MaterialTheme.colorScheme.error, fontSize = 13.sp)
            }

            Button(
                onClick = {
                    val port = manualPort.toIntOrNull() ?: 8000
                    onConnectToPeer(manualHost.trim(), port, pinCode.trim())
                },
                enabled = manualHost.isNotBlank() && pinCode.length >= 6 && !isConnecting,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp)
            ) {
                if (isConnecting) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary)
                } else {
                    Text("Pair & Connect", fontSize = 16.sp)
                }
            }
        }
    }
}
