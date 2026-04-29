package com.ozkanilkay.musiki_frontend.ui.library

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.components.AddToPlaylistSheet
import com.ozkanilkay.musiki_frontend.ui.components.SongRow
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LikedSongsScreen(
    playerViewModel: PlayerViewModel,
    onBack: () -> Unit,
    onOpenArtist: (Int) -> Unit,
    viewModel: LikedSongsViewModel = hiltViewModel(),
) {
    val songs by viewModel.songs.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val currentSong by playerViewModel.currentSong.collectAsState()
    val isPlaying by playerViewModel.isPlaying.collectAsState()
    val c = Musiki.colors

    var sheetFor by remember { mutableStateOf<SongDto?>(null) }

    Scaffold(
        containerColor = c.background,
        contentWindowInsets = WindowInsets(0),
        topBar = {
            TopAppBar(
                title = { Text("Beğenilen Şarkılar", color = c.textPrimary) },
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
                isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
                error != null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(error!!, color = c.error)
                }
                songs.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Henüz beğendiğin şarkı yok", color = c.textSecondary)
                }
                else -> LazyColumn {
                    itemsIndexed(songs, key = { _, s -> s.id }) { index, song ->
                        SongRow(
                            song = song,
                            isCurrentlyPlaying = currentSong?.id == song.id && isPlaying,
                            isCurrentSong = currentSong?.id == song.id,
                            onClick = { playerViewModel.playQueue(songs, index) },
                            onLikeToggle = { viewModel.unlike(it) },
                            onMoreClick = { sheetFor = it },
                            onArtistClick = onOpenArtist,
                            isLikedOverride = true,
                        )
                        HorizontalDivider(color = c.outline, thickness = 1.dp)
                    }
                }
            }
        }
    }

    sheetFor?.let { song ->
        AddToPlaylistSheet(song = song, onDismiss = { sheetFor = null })
    }
}
