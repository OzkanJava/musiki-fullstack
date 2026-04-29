package com.ozkanilkay.musiki_frontend.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.components.ArtistCard
import com.ozkanilkay.musiki_frontend.ui.components.SongCover
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@Composable
fun HomeScreen(
    playerViewModel: PlayerViewModel,
    onOpenArtist: (Int) -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val recentlyPlayed by viewModel.recentlyPlayed.collectAsState()
    val forYou by viewModel.forYou.collectAsState()
    val artists by viewModel.artists.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val currentSong by playerViewModel.currentSong.collectAsState()
    val c = Musiki.colors

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(c.background),
    ) {
        // Header
        Column(modifier = Modifier.padding(horizontal = 20.dp, vertical = 20.dp)) {
            Text(
                text = "musiki",
                style = MaterialTheme.typography.headlineLarge,
                color = c.primary,
            )
            Text(
                text = "Hoş geldin",
                style = MaterialTheme.typography.titleMedium,
                color = c.textSecondary,
            )
        }

        val isEmpty = recentlyPlayed.isEmpty() && forYou.isEmpty() && artists.isEmpty()

        when {
            isLoading && isEmpty -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
            }
            error != null && isEmpty -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text(error!!, color = c.error, style = MaterialTheme.typography.bodyMedium)
                        Button(
                            onClick = viewModel::loadAll,
                            colors = ButtonDefaults.buttonColors(containerColor = c.primary),
                        ) { Text("Tekrar Dene") }
                    }
                }
            }
            else -> {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (artists.isNotEmpty()) {
                        item { ShelfTitle("Sanatçılar") }
                        item {
                            LazyRow(
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                                contentPadding = PaddingValues(horizontal = 16.dp),
                            ) {
                                items(artists, key = { it.id }) { artist ->
                                    ArtistCard(
                                        name = artist.username,
                                        onClick = { onOpenArtist(artist.id) },
                                    )
                                }
                            }
                        }
                    }
                    if (recentlyPlayed.isNotEmpty()) {
                        item { ShelfTitle("Son çalınanlar") }
                        item {
                            HorizontalSongShelf(
                                songs = recentlyPlayed,
                                currentSongId = currentSong?.id,
                                onSongClick = { song ->
                                    playerViewModel.playQueue(recentlyPlayed, recentlyPlayed.indexOf(song))
                                },
                            )
                        }
                    }
                    if (forYou.isNotEmpty()) {
                        item { ShelfTitle("Senin için") }
                        item {
                            HorizontalSongShelf(
                                songs = forYou,
                                currentSongId = currentSong?.id,
                                onSongClick = { song ->
                                    playerViewModel.playQueue(forYou, forYou.indexOf(song))
                                },
                            )
                        }
                    }
                    item { Spacer(Modifier.height(24.dp)) }
                }
            }
        }
    }
}

@Composable
private fun ShelfTitle(text: String) {
    val c = Musiki.colors
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        color = c.textPrimary,
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
    )
}

@Composable
private fun HorizontalSongShelf(
    songs: List<SongDto>,
    currentSongId: Int?,
    onSongClick: (SongDto) -> Unit,
) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(horizontal = 16.dp),
    ) {
        items(songs, key = { it.id }) { song ->
            ShelfSongCard(
                song = song,
                isCurrent = currentSongId == song.id,
                onClick = { onSongClick(song) },
            )
        }
    }
}

@Composable
private fun ShelfSongCard(song: SongDto, isCurrent: Boolean, onClick: () -> Unit) {
    val c = Musiki.colors
    Column(
        modifier = Modifier
            .width(140.dp)
            .clickable(onClick = onClick),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        SongCover(coverUrl = song.cover_image, size = 140.dp)
        Text(
            text = song.title,
            style = MaterialTheme.typography.bodyMedium,
            color = if (isCurrent) c.primary else c.textPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = song.artist.username,
            style = MaterialTheme.typography.bodySmall,
            color = c.textSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}
