package com.ozkanilkay.musiki_frontend.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@Composable
fun SongCover(coverUrl: String?, size: Dp, modifier: Modifier = Modifier) {
    val c = Musiki.colors
    val shape = RoundedCornerShape(8.dp)
    if (!coverUrl.isNullOrBlank()) {
        AsyncImage(
            model = coverUrl,
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = modifier.size(size).clip(shape),
        )
    } else {
        Box(
            modifier = modifier
                .size(size)
                .clip(shape)
                .background(c.gray),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Default.MusicNote,
                contentDescription = null,
                tint = c.textSecondary,
                modifier = Modifier.size(size * 0.5f),
            )
        }
    }
}

/**
 * Ortak şarkı satırı. Kalp ve daha fazla-menüsü opsiyonel.
 */
@Composable
fun SongRow(
    song: SongDto,
    isCurrentlyPlaying: Boolean,
    isCurrentSong: Boolean,
    onClick: () -> Unit,
    onLikeToggle: ((SongDto) -> Unit)? = null,
    onMoreClick: ((SongDto) -> Unit)? = null,
    onArtistClick: ((Int) -> Unit)? = null,
    isLikedOverride: Boolean? = null,
) {
    val c = Musiki.colors
    val liked = isLikedOverride ?: song.is_liked
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        SongCover(coverUrl = song.cover_image, size = 52.dp)

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = song.title,
                style = MaterialTheme.typography.bodyLarge,
                color = if (isCurrentSong) c.primary else c.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = song.artist.username,
                style = MaterialTheme.typography.bodySmall,
                color = c.textSecondary,
                maxLines = 1,
                modifier = if (onArtistClick != null) {
                    Modifier.clickable { onArtistClick(song.artist.id) }
                } else Modifier,
            )
        }

        if (isCurrentlyPlaying) {
            Icon(
                imageVector = Icons.Default.MusicNote,
                contentDescription = null,
                tint = c.primary,
                modifier = Modifier.size(18.dp),
            )
        }

        if (onLikeToggle != null) {
            IconButton(onClick = { onLikeToggle(song) }) {
                Icon(
                    imageVector = if (liked) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                    contentDescription = if (liked) "Beğeniyi kaldır" else "Beğen",
                    tint = if (liked) c.secondary else c.textSecondary,
                )
            }
        }

        if (onMoreClick != null) {
            IconButton(onClick = { onMoreClick(song) }) {
                Icon(
                    imageVector = Icons.Default.MoreVert,
                    contentDescription = "Daha fazla",
                    tint = c.textSecondary,
                )
            }
        }
    }
}
