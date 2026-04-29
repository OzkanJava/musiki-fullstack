package com.ozkanilkay.musiki_frontend.ui.detail

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.components.SongCover
import com.ozkanilkay.musiki_frontend.ui.components.SongRow
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlbumDetailScreen(
    onBack: () -> Unit,
    onArtistClick: (Int) -> Unit,
    playerViewModel: PlayerViewModel,
    viewModel: AlbumDetailViewModel = hiltViewModel(),
) {
    val album by viewModel.album.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val currentSong by playerViewModel.currentSong.collectAsState()
    val isPlaying by playerViewModel.isPlaying.collectAsState()
    val c = Musiki.colors

    var sheetSong by remember { mutableStateOf<SongDto?>(null) }

    Scaffold(
        containerColor = c.background,
        topBar = {
            TopAppBar(
                title = {
                    Text(album?.title ?: "Albüm", color = c.textPrimary, maxLines = 1, overflow = TextOverflow.Ellipsis)
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
                isLoading && album == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
                album == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(error ?: "Albüm bulunamadı", color = c.textSecondary)
                }
                else -> {
                    val a = album!!
                    LazyColumn {
                        item {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(20.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(12.dp),
                            ) {
                                SongCover(coverUrl = a.cover_image, size = 200.dp)
                                Text(
                                    a.title,
                                    style = MaterialTheme.typography.headlineSmall,
                                    color = c.textPrimary,
                                    textAlign = TextAlign.Center,
                                )
                                TextButton(onClick = { onArtistClick(a.artist.id) }) {
                                    Text(a.artist.username, color = c.textSecondary)
                                }
                                if (a.description.isNotBlank()) {
                                    Text(
                                        a.description,
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = c.textSecondary,
                                        textAlign = TextAlign.Center,
                                    )
                                }
                                Text(
                                    "${a.song_count} şarkı",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = c.textSecondary,
                                )
                                Button(
                                    onClick = {
                                        if (a.songs.isNotEmpty()) {
                                            playerViewModel.playQueue(a.songs, 0)
                                        }
                                    },
                                    enabled = a.songs.isNotEmpty(),
                                    colors = ButtonDefaults.buttonColors(containerColor = c.primary),
                                    modifier = Modifier.fillMaxWidth().height(48.dp),
                                ) {
                                    Icon(Icons.Default.PlayArrow, contentDescription = null, tint = c.onPrimary)
                                    Spacer(Modifier.width(6.dp))
                                    Text("Çal", color = c.onPrimary)
                                }
                            }
                            HorizontalDivider(color = c.outline, thickness = 1.dp)
                        }
                        itemsIndexed(a.songs, key = { _, s -> s.id }) { index, song ->
                            SongRow(
                                song = song,
                                isCurrentlyPlaying = currentSong?.id == song.id && isPlaying,
                                isCurrentSong = currentSong?.id == song.id,
                                onClick = { playerViewModel.playQueue(a.songs, index) },
                                onLikeToggle = { viewModel.toggleSongLike(it.id) },
                                onMoreClick = { sheetSong = it },
                            )
                            HorizontalDivider(
                                color = c.outline,
                                thickness = 1.dp,
                                modifier = Modifier.padding(horizontal = 16.dp),
                            )
                        }
                        item { Spacer(Modifier.height(24.dp)) }
                    }
                }
            }
        }
    }

    sheetSong?.let { song ->
        com.ozkanilkay.musiki_frontend.ui.components.AddToPlaylistSheet(
            song = song,
            onDismiss = { sheetSong = null },
        )
    }
}
