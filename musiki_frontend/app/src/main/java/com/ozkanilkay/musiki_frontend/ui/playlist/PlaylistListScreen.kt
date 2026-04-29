package com.ozkanilkay.musiki_frontend.ui.playlist

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.QueueMusic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlaylistListScreen(
    onBack: () -> Unit,
    onOpenPlaylist: (Int) -> Unit,
    onCreate: () -> Unit,
    viewModel: PlaylistListViewModel = hiltViewModel(),
) {
    val playlists by viewModel.playlists.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val c = Musiki.colors

    // Ekran her gösterildiğinde yeniden yükle (create ekranından dönüş için)
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        containerColor = c.background,
        topBar = {
            TopAppBar(
                title = { Text("Playlistlerim", color = c.textPrimary) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Geri", tint = c.textPrimary)
                    }
                },
                windowInsets = WindowInsets(0),
                colors = TopAppBarDefaults.topAppBarColors(containerColor = c.background),
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onCreate,
                containerColor = c.primary,
            ) {
                Icon(Icons.Default.Add, contentDescription = "Yeni Playlist")
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
                playlists.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Henüz playlist yok.\n+ ile oluştur.", color = c.textSecondary)
                }
                else -> LazyColumn {
                    items(playlists, key = { it.id }) { pl ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onOpenPlaylist(pl.id) }
                                .padding(horizontal = 16.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(56.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(c.gray),
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(Icons.Default.QueueMusic, contentDescription = null, tint = c.primary)
                            }
                            Column(Modifier.weight(1f)) {
                                Text(
                                    pl.title,
                                    color = c.textPrimary,
                                    style = MaterialTheme.typography.bodyLarge,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                Text(
                                    "${pl.item_count} şarkı",
                                    color = c.textSecondary,
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                            IconButton(onClick = { viewModel.delete(pl.id) }) {
                                Icon(Icons.Default.Delete, contentDescription = "Sil", tint = c.textSecondary)
                            }
                        }
                        HorizontalDivider(color = c.outline, thickness = 1.dp)
                    }
                }
            }
        }
    }
}
