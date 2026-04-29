package com.ozkanilkay.musiki_frontend.ui.playlist

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.QueueMusic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.components.SongCover
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlaylistDetailScreen(
    playlistId: Int,
    playerViewModel: PlayerViewModel,
    onBack: () -> Unit,
    viewModel: PlaylistDetailViewModel = hiltViewModel(),
) {
    val detail by viewModel.detail.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val currentSong by playerViewModel.currentSong.collectAsState()
    val c = Musiki.colors

    Scaffold(
        containerColor = c.background,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        detail?.title ?: "Playlist",
                        color = c.textPrimary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Geri", tint = c.textPrimary)
                    }
                },
                windowInsets = WindowInsets(0),
                colors = TopAppBarDefaults.topAppBarColors(containerColor = c.background),
            )
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when {
                isLoading && detail == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
                detail == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Playlist bulunamadı", color = c.textSecondary)
                }
                else -> {
                    val d = detail!!
                    LazyColumn {
                        item {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(20.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(12.dp),
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(180.dp)
                                        .clip(RoundedCornerShape(12.dp))
                                        .background(c.gray),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    Icon(
                                        Icons.Default.QueueMusic,
                                        contentDescription = null,
                                        tint = c.primary,
                                        modifier = Modifier.size(80.dp),
                                    )
                                }
                                Text(
                                    d.title,
                                    style = MaterialTheme.typography.headlineSmall,
                                    color = c.textPrimary,
                                )
                                if (d.description.isNotBlank()) {
                                    Text(
                                        d.description,
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = c.textSecondary,
                                    )
                                }
                                Text(
                                    "${d.item_count} şarkı",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = c.textSecondary,
                                )
                                Button(
                                    onClick = {
                                        if (d.items.isNotEmpty()) {
                                            playerViewModel.playQueue(d.items.map { it.song }, 0)
                                        }
                                    },
                                    enabled = d.items.isNotEmpty(),
                                    colors = ButtonDefaults.buttonColors(containerColor = c.primary),
                                    modifier = Modifier.fillMaxWidth().height(48.dp),
                                ) {
                                    Icon(Icons.Default.PlayArrow, contentDescription = null, tint = c.onPrimary)
                                    Spacer(Modifier.width(6.dp))
                                    Text("Çal", color = c.onPrimary)
                                }
                            }
                        }
                        itemsIndexed(d.items, key = { _, it -> it.id }) { index, item ->
                            val song = item.song
                            val isCurrent = currentSong?.id == song.id
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        playerViewModel.playQueue(d.items.map { it.song }, index)
                                    }
                                    .padding(horizontal = 16.dp, vertical = 10.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                            ) {
                                SongCover(coverUrl = song.cover_image, size = 52.dp)
                                Column(
                                    modifier = Modifier
                                        .weight(1f)
                                        .padding(end = 4.dp),
                                ) {
                                    Text(
                                        song.title,
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = if (isCurrent) c.primary else c.textPrimary,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    Text(
                                        song.artist.username,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = c.textSecondary,
                                        maxLines = 1,
                                    )
                                }
                                IconButton(onClick = { viewModel.removeItem(item.id) }) {
                                    Icon(Icons.Default.Delete, contentDescription = "Çıkar", tint = c.textSecondary)
                                }
                            }
                            HorizontalDivider(color = c.outline, thickness = 1.dp)
                        }
                        item { Spacer(Modifier.height(24.dp)) }
                    }
                }
            }
        }
    }
}
