package com.ozkanilkay.musiki_frontend.ui.detail

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.data.model.AlbumDto
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.components.AddToPlaylistSheet
import com.ozkanilkay.musiki_frontend.ui.components.SongCover
import com.ozkanilkay.musiki_frontend.ui.components.SongRow
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ArtistDetailScreen(
    onBack: () -> Unit,
    onAlbumClick: (Int) -> Unit,
    playerViewModel: PlayerViewModel,
    viewModel: ArtistDetailViewModel = hiltViewModel(),
) {
    val artist by viewModel.artist.collectAsState()
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
                title = { Text(artist?.username ?: "Sanatçı", color = c.textPrimary, maxLines = 1, overflow = TextOverflow.Ellipsis) },
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
                isLoading && artist == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
                artist == null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(error ?: "Sanatçı bulunamadı", color = c.textSecondary)
                }
                else -> {
                    val a = artist!!
                    LazyColumn {
                        item {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(20.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(12.dp),
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(140.dp)
                                        .clip(CircleShape)
                                        .background(c.gray),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    Icon(Icons.Default.Person, contentDescription = null, tint = c.textSecondary, modifier = Modifier.size(80.dp))
                                }
                                Text(a.username, style = MaterialTheme.typography.headlineSmall, color = c.textPrimary)
                                Text(
                                    "${a.songs_count} şarkı",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = c.textSecondary,
                                )
                            }
                        }

                        if (a.albums.isNotEmpty()) {
                            item {
                                Text(
                                    "Albümler",
                                    style = MaterialTheme.typography.titleMedium,
                                    color = c.textPrimary,
                                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                )
                            }
                            item {
                                LazyRow(
                                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                                    contentPadding = PaddingValues(horizontal = 16.dp),
                                ) {
                                    items(a.albums, key = { it.id }) { album ->
                                        AlbumCard(album = album, onClick = { onAlbumClick(album.id) })
                                    }
                                }
                            }
                        }

                        if (a.songs.isNotEmpty()) {
                            item {
                                Text(
                                    "Popüler Şarkılar",
                                    style = MaterialTheme.typography.titleMedium,
                                    color = c.textPrimary,
                                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                )
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
                        }
                        item { Spacer(Modifier.height(24.dp)) }
                    }
                }
            }
        }
    }

    sheetSong?.let { song ->
        AddToPlaylistSheet(song = song, onDismiss = { sheetSong = null })
    }
}

@Composable
private fun AlbumCard(album: AlbumDto, onClick: () -> Unit) {
    val c = Musiki.colors
    Column(
        modifier = Modifier
            .width(140.dp)
            .clickable(onClick = onClick),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        SongCover(coverUrl = album.cover_image, size = 140.dp)
        Text(
            album.title,
            style = MaterialTheme.typography.bodyMedium,
            color = c.textPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            "${album.song_count} şarkı",
            style = MaterialTheme.typography.bodySmall,
            color = c.textSecondary,
        )
    }
}
