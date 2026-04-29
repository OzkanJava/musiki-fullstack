package com.ozkanilkay.musiki_frontend.ui.library

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.LibraryMusic
import androidx.compose.material.icons.filled.QueueMusic
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.ozkanilkay.musiki_frontend.ui.navigation.Screen
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@Composable
fun LibraryScreen(onNavigate: (String) -> Unit) {
    val c = Musiki.colors
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(c.background)
            .padding(horizontal = 20.dp, vertical = 20.dp),
    ) {
        Text(
            text = "Kütüphanem",
            style = MaterialTheme.typography.headlineMedium,
            color = c.textPrimary,
        )
        Spacer(Modifier.height(20.dp))

        LibraryCard(
            icon = Icons.Default.Favorite,
            title = "Beğenilen Şarkılar",
            subtitle = "Kalp attığın şarkılar",
            onClick = { onNavigate(Screen.LikedSongs.route) },
        )
        Spacer(Modifier.height(12.dp))
        LibraryCard(
            icon = Icons.Default.QueueMusic,
            title = "Playlistlerim",
            subtitle = "Kendi çalma listelerin",
            onClick = { onNavigate(Screen.PlaylistList.route) },
        )
        Spacer(Modifier.height(12.dp))
        LibraryCard(
            icon = Icons.Default.LibraryMusic,
            title = "Cihazımdaki Müzikler",
            subtitle = "Yerel dosyalardan dinle",
            onClick = { onNavigate(Screen.LocalMusic.route) },
        )
    }
}

@Composable
private fun LibraryCard(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
) {
    val c = Musiki.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(c.darkGray)
            .clickable(onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Box(
            modifier = Modifier
                .size(48.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(c.primary.copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = c.primary)
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = c.textPrimary)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = c.textSecondary)
        }
    }
}
