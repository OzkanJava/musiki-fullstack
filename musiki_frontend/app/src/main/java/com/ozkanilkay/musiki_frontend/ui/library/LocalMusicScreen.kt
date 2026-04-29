package com.ozkanilkay.musiki_frontend.ui.library

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.data.model.LocalTrack
import com.ozkanilkay.musiki_frontend.data.model.toSongDto
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

private fun audioPermission(): String =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        Manifest.permission.READ_MEDIA_AUDIO
    } else {
        Manifest.permission.READ_EXTERNAL_STORAGE
    }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LocalMusicScreen(
    playerViewModel: PlayerViewModel,
    onBack: () -> Unit,
    viewModel: LocalMusicViewModel = hiltViewModel(),
) {
    val tracks by viewModel.tracks.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val hasPermission by viewModel.hasPermission.collectAsState()
    val currentSong by playerViewModel.currentSong.collectAsState()
    val isPlaying by playerViewModel.isPlaying.collectAsState()
    val c = Musiki.colors
    val context = LocalContext.current

    val permission = remember { audioPermission() }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) viewModel.onPermissionGranted()
    }

    LaunchedEffect(Unit) {
        val granted = ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
        if (granted) viewModel.onPermissionGranted() else launcher.launch(permission)
    }

    Scaffold(
        containerColor = c.background,
        contentWindowInsets = WindowInsets(0),
        topBar = {
            TopAppBar(
                title = { Text("Cihazımdaki Müzikler", color = c.textPrimary) },
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
                !hasPermission -> Column(
                    Modifier.fillMaxSize().padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        "Cihazındaki müzikleri listelemek için izin gerekli.",
                        color = c.textSecondary,
                    )
                    Spacer(Modifier.height(12.dp))
                    Button(
                        onClick = { launcher.launch(permission) },
                        colors = ButtonDefaults.buttonColors(containerColor = c.primary),
                    ) { Text("İzin Ver", color = c.onPrimary) }
                }
                isLoading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
                tracks.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        "Music/ veya Download/ klasöründe müzik bulunamadı",
                        color = c.textSecondary,
                    )
                }
                else -> {
                    val songDtos = remember(tracks) { tracks.map { it.toSongDto() } }
                    val uriMap = remember(tracks) { tracks.associate { it.id.toInt() to it.contentUri.toString() } }
                    LazyColumn {
                        itemsIndexed(tracks, key = { _, t -> t.id }) { index, track ->
                            LocalTrackRow(
                                track = track,
                                isCurrent = currentSong?.id == track.id.toInt(),
                                isPlaying = isPlaying && currentSong?.id == track.id.toInt(),
                                onClick = {
                                    playerViewModel.playQueue(
                                        songs = songDtos,
                                        startIndex = index,
                                        uriResolver = { song -> uriMap[song.id] ?: "" },
                                        forceMimeType = null,
                                    )
                                },
                            )
                            HorizontalDivider(color = c.outline, thickness = 1.dp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LocalTrackRow(
    track: LocalTrack,
    isCurrent: Boolean,
    isPlaying: Boolean,
    onClick: () -> Unit,
) {
    val c = Musiki.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            Icons.Default.LibraryMusic,
            contentDescription = null,
            tint = if (isCurrent) c.primary else c.textSecondary,
        )
        Column(Modifier.weight(1f)) {
            Text(
                track.title,
                color = if (isCurrent) c.primary else c.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                track.artist,
                color = c.textSecondary,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        if (isPlaying) {
            Text("▶", color = c.primary)
        }
    }
}
