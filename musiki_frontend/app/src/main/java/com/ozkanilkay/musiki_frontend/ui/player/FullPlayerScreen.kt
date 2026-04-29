package com.ozkanilkay.musiki_frontend.ui.player

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.QueueMusic
import androidx.compose.material.icons.filled.Repeat
import androidx.compose.material.icons.filled.RepeatOne
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.player.RepeatMode
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@Composable
fun FullPlayerScreen(
    playerViewModel: PlayerViewModel,
    onNavigateBack: () -> Unit,
    onOpenArtist: (Int) -> Unit,
) {
    val song by playerViewModel.currentSong.collectAsState()
    val isPlaying by playerViewModel.isPlaying.collectAsState()
    val position by playerViewModel.position.collectAsState()
    val duration by playerViewModel.duration.collectAsState()
    val shuffleEnabled by playerViewModel.shuffleEnabled.collectAsState()
    val repeatMode by playerViewModel.repeatMode.collectAsState()
    val c = Musiki.colors

    var showQueue by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(c.background)
            .padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        // Top bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onNavigateBack) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Geri",
                    tint = c.textPrimary,
                )
            }
            Text(
                text = "Şimdi Çalıyor",
                style = MaterialTheme.typography.titleMedium,
                color = c.textSecondary,
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center,
            )
            IconButton(onClick = { showQueue = true }) {
                Icon(
                    imageVector = Icons.Default.QueueMusic,
                    contentDescription = "Sıra",
                    tint = c.textPrimary,
                )
            }
        }

        Spacer(Modifier.height(24.dp))

        // Cover art
        val coverUrl = song?.cover_image
        if (!coverUrl.isNullOrBlank()) {
            AsyncImage(
                model = coverUrl,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(280.dp)
                    .clip(RoundedCornerShape(16.dp)),
            )
        } else {
            Box(
                modifier = Modifier
                    .size(280.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(c.gray),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.Default.MusicNote,
                    contentDescription = null,
                    tint = c.textSecondary,
                    modifier = Modifier.size(80.dp),
                )
            }
        }

        Spacer(Modifier.height(32.dp))

        // Song info
        Text(
            text = song?.title ?: "",
            style = MaterialTheme.typography.headlineSmall,
            color = c.textPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(4.dp))
        Text(
            text = song?.artist?.username ?: "",
            style = MaterialTheme.typography.bodyLarge,
            color = c.textSecondary,
            modifier = Modifier.clickable(enabled = song != null) {
                song?.artist?.id?.let(onOpenArtist)
            },
        )

        Spacer(Modifier.height(16.dp))

        val liked = song?.is_liked == true
        IconButton(onClick = { playerViewModel.toggleCurrentLike() }) {
            Icon(
                imageVector = if (liked) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                contentDescription = if (liked) "Beğeniyi kaldır" else "Beğen",
                tint = if (liked) c.secondary else c.textSecondary,
                modifier = Modifier.size(28.dp),
            )
        }

        Spacer(Modifier.height(16.dp))

        // Seek bar
        Slider(
            value = if (duration > 0) position.toFloat() / duration else 0f,
            onValueChange = { fraction ->
                playerViewModel.seekTo((fraction * duration).toLong())
            },
            modifier = Modifier.fillMaxWidth(),
            colors = SliderDefaults.colors(
                thumbColor = c.primary,
                activeTrackColor = c.primary,
                inactiveTrackColor = c.gray,
            ),
        )

        // Time labels
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(position.toTimeString(), style = MaterialTheme.typography.bodySmall, color = c.textSecondary)
            Text(duration.toTimeString(), style = MaterialTheme.typography.bodySmall, color = c.textSecondary)
        }

        Spacer(Modifier.height(24.dp))

        // Playback controls
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = { playerViewModel.toggleShuffle() }) {
                Icon(
                    imageVector = Icons.Default.Shuffle,
                    contentDescription = "Karıştır",
                    tint = if (shuffleEnabled) c.primary else c.textSecondary,
                )
            }

            IconButton(
                onClick = { playerViewModel.previous() },
                modifier = Modifier.size(52.dp),
            ) {
                Icon(
                    Icons.Default.SkipPrevious,
                    contentDescription = "Önceki",
                    tint = c.textPrimary,
                    modifier = Modifier.size(36.dp),
                )
            }

            // Play / Pause  — bigger circle button
            FilledIconButton(
                onClick = playerViewModel::togglePlayPause,
                modifier = Modifier.size(64.dp),
                shape = CircleShape,
                colors = IconButtonDefaults.filledIconButtonColors(
                    containerColor = c.primary,
                ),
            ) {
                Icon(
                    imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                    contentDescription = if (isPlaying) "Duraklat" else "Çal",
                    tint = c.onPrimary,
                    modifier = Modifier.size(36.dp),
                )
            }

            IconButton(
                onClick = { playerViewModel.next() },
                modifier = Modifier.size(52.dp),
            ) {
                Icon(
                    Icons.Default.SkipNext,
                    contentDescription = "Sonraki",
                    tint = c.textPrimary,
                    modifier = Modifier.size(36.dp),
                )
            }

            IconButton(onClick = { playerViewModel.cycleRepeatMode() }) {
                Icon(
                    imageVector = if (repeatMode == RepeatMode.ONE) Icons.Default.RepeatOne else Icons.Default.Repeat,
                    contentDescription = "Tekrar",
                    tint = if (repeatMode != RepeatMode.OFF) c.primary else c.textSecondary,
                )
            }
        }
    }

    if (showQueue) {
        QueueSheet(
            playerViewModel = playerViewModel,
            onDismiss = { showQueue = false },
        )
    }
}

private fun Long.toTimeString(): String {
    val totalSec = this / 1000
    return "%d:%02d".format(totalSec / 60, totalSec % 60)
}
