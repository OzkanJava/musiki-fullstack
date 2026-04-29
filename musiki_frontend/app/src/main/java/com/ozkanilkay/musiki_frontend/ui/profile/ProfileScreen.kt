package com.ozkanilkay.musiki_frontend.ui.profile

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.SettingsBrightness
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.data.model.ListenHistoryDto
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki
import com.ozkanilkay.musiki_frontend.ui.theme.ThemeMode
import com.ozkanilkay.musiki_frontend.ui.theme.musikiTextFieldColors

@Composable
fun ProfileScreen(
    onLogout: () -> Unit,
    onNavigateToUpload: () -> Unit,
    viewModel: ProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val themeMode by viewModel.themeMode.collectAsState()
    var showArtistDialog by remember { mutableStateOf(false) }

    val c = Musiki.colors

    if (showArtistDialog) {
        ArtistRequestDialog(
            isLoading = state.requestArtistLoading,
            onConfirm = { bio ->
                viewModel.requestArtist(bio)
                showArtistDialog = false
            },
            onDismiss = { showArtistDialog = false },
        )
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(c.background),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // ── Profil Kartı ──────────────────────────────────────────────────
        item {
            ProfileCard(
                state = state,
                onLogout = { viewModel.logout(onLogout) },
                onRequestArtist = { showArtistDialog = true },
                onNavigateToUpload = onNavigateToUpload,
            )
        }

        // ── Tema Seçimi ──────────────────────────────────────────────────
        item {
            ThemeSelectorCard(
                currentMode = themeMode,
                onModeSelected = viewModel::setThemeMode,
            )
        }

        // ── Dinleme Geçmişi Başlığı ───────────────────────────────────────
        if (state.history.isNotEmpty()) {
            item {
                Text(
                    text = "Son Dinlenenler",
                    style = MaterialTheme.typography.titleMedium,
                    color = c.textPrimary,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }

            items(state.history.take(20)) { entry ->
                HistoryRow(entry)
            }
        }

        if (state.isLoading) {
            item {
                Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary, modifier = Modifier.size(32.dp))
                }
            }
        }

        if (state.error != null) {
            item {
                Text(state.error!!, color = c.error, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

// ── Theme Selector ───────────────────────────────────────────────────────────

@Composable
private fun ThemeSelectorCard(
    currentMode: ThemeMode,
    onModeSelected: (ThemeMode) -> Unit,
) {
    val c = Musiki.colors

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = c.surface),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Tema",
                style = MaterialTheme.typography.titleMedium,
                color = c.textPrimary,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                ThemeOption(
                    label = "Koyu",
                    icon = Icons.Default.DarkMode,
                    isSelected = currentMode == ThemeMode.DARK,
                    onClick = { onModeSelected(ThemeMode.DARK) },
                    modifier = Modifier.weight(1f),
                )
                ThemeOption(
                    label = "Açık",
                    icon = Icons.Default.LightMode,
                    isSelected = currentMode == ThemeMode.LIGHT,
                    onClick = { onModeSelected(ThemeMode.LIGHT) },
                    modifier = Modifier.weight(1f),
                )
                ThemeOption(
                    label = "Cihaz",
                    icon = Icons.Default.SettingsBrightness,
                    isSelected = currentMode == ThemeMode.SYSTEM,
                    onClick = { onModeSelected(ThemeMode.SYSTEM) },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun ThemeOption(
    label: String,
    icon: ImageVector,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val c = Musiki.colors
    val bgColor by animateColorAsState(
        if (isSelected) c.primary.copy(alpha = 0.15f) else c.surfaceHigh,
        label = "themeBg",
    )
    val borderColor by animateColorAsState(
        if (isSelected) c.primary else c.outline.copy(alpha = 0.4f),
        label = "themeBorder",
    )
    val contentColor by animateColorAsState(
        if (isSelected) c.primary else c.textSecondary,
        label = "themeContent",
    )

    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .border(1.5.dp, borderColor, RoundedCornerShape(12.dp))
            .background(bgColor)
            .clickable(onClick = onClick)
            .padding(vertical = 14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Icon(icon, contentDescription = label, tint = contentColor, modifier = Modifier.size(24.dp))
        Text(label, style = MaterialTheme.typography.labelMedium, color = contentColor)
    }
}

// ── Profile Card ─────────────────────────────────────────────────────────────

@Composable
private fun ProfileCard(
    state: ProfileUiState,
    onLogout: () -> Unit,
    onRequestArtist: () -> Unit,
    onNavigateToUpload: () -> Unit,
) {
    val user = state.user
    val c = Musiki.colors

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = c.surface),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                // Avatar
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .clip(CircleShape)
                        .background(c.primary.copy(alpha = 0.2f)),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        imageVector = Icons.Default.Person,
                        contentDescription = null,
                        tint = c.primary,
                        modifier = Modifier.size(32.dp),
                    )
                }

                Column {
                    Text(
                        text = user?.username ?: "—",
                        style = MaterialTheme.typography.titleLarge,
                        color = c.textPrimary,
                        fontWeight = FontWeight.Bold,
                    )
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RoleBadge(user?.role ?: "listener", user?.isApprovedArtist ?: false)
                        if (user?.email?.isNotBlank() == true) {
                            Text(
                                text = user.email,
                                style = MaterialTheme.typography.bodySmall,
                                color = c.textSecondary,
                            )
                        }
                    }
                }
            }

            if (user?.bio?.isNotBlank() == true) {
                Text(
                    text = user.bio,
                    style = MaterialTheme.typography.bodyMedium,
                    color = c.textSecondary,
                )
            }

            HorizontalDivider(color = c.textSecondary.copy(alpha = 0.15f))

            // ── Sanatçı ise: Şarkı Yükle butonu (tam genişlik) ───────────────
            if (user?.isApprovedArtist == true) {
                Button(
                    onClick = onNavigateToUpload,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = c.secondary,
                        contentColor = c.onSecondary,
                    ),
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Icon(
                        Icons.Default.CloudUpload,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("Şarkı Yükle")
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Sanatçı ol butonu (sadece listener'a)
                if (user?.role == "listener") {
                    OutlinedButton(
                        onClick = onRequestArtist,
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = c.secondary),
                        border = androidx.compose.foundation.BorderStroke(1.dp, c.secondary),
                    ) {
                        Icon(Icons.Default.MusicNote, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Sanatçı Ol")
                    }
                }

                Button(
                    onClick = onLogout,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = c.error),
                    shape = RoundedCornerShape(10.dp),
                ) {
                    Text("Çıkış Yap")
                }
            }
        }
    }
}

@Composable
private fun RoleBadge(role: String, isApproved: Boolean) {
    val c = Musiki.colors
    val (label, color) = when {
        role == "admin" -> "Yönetici" to c.error
        role == "artist" && isApproved -> "Sanatçı" to c.secondary
        role == "artist" -> "Sanatçı (Onay Bekliyor)" to c.textSecondary
        else -> "Dinleyici" to c.textSecondary
    }
    Surface(
        color = color.copy(alpha = 0.15f),
        shape = RoundedCornerShape(6.dp),
    ) {
        Text(
            text = label,
            color = color,
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
        )
    }
}

@Composable
private fun HistoryRow(entry: ListenHistoryDto) {
    val c = Musiki.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(c.surface, RoundedCornerShape(10.dp))
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            imageVector = Icons.Default.MusicNote,
            contentDescription = null,
            tint = c.primary,
            modifier = Modifier.size(20.dp),
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = entry.song.title,
                style = MaterialTheme.typography.bodyMedium,
                color = c.textPrimary,
                maxLines = 1,
            )
            Text(
                text = entry.song.artist.username,
                style = MaterialTheme.typography.bodySmall,
                color = c.textSecondary,
            )
        }
    }
}

@Composable
private fun ArtistRequestDialog(
    isLoading: Boolean,
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val c = Musiki.colors
    var bio by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = c.surface,
        title = { Text("Sanatçı Başvurusu", color = c.textPrimary) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "Sanatçı hesabı açmak için kısa bir biyografi yaz.",
                    color = c.textSecondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
                OutlinedTextField(
                    value = bio,
                    onValueChange = { bio = it },
                    label = { Text("Biyografi") },
                    minLines = 3,
                    colors = musikiTextFieldColors(),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onConfirm(bio) },
                enabled = bio.isNotBlank() && !isLoading,
                colors = ButtonDefaults.buttonColors(containerColor = c.primary),
            ) {
                if (isLoading) CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                else Text("Başvur", color = c.onPrimary)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("İptal", color = c.textSecondary)
            }
        },
    )
}
