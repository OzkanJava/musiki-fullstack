package com.ozkanilkay.musiki_frontend.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.QueueMusic
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.PlaylistDto
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.data.repository.PlaylistRepository
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki
import com.ozkanilkay.musiki_frontend.ui.theme.musikiTextFieldColors
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AddToPlaylistViewModel @Inject constructor(
    private val repo: PlaylistRepository,
) : ViewModel() {
    private val _playlists = MutableStateFlow<List<PlaylistDto>>(emptyList())
    val playlists = _playlists.asStateFlow()
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()
    private val _addedIds = MutableStateFlow<Set<Int>>(emptySet())
    val addedIds = _addedIds.asStateFlow()
    private val _message = MutableStateFlow<String?>(null)
    val message = _message.asStateFlow()

    fun load() = viewModelScope.launch {
        _isLoading.value = true
        repo.getPlaylists().onSuccess { _playlists.value = it }
        _isLoading.value = false
    }

    fun addSong(playlistId: Int, songId: Int) = viewModelScope.launch {
        repo.addSong(playlistId, songId)
            .onSuccess {
                _addedIds.value = _addedIds.value + playlistId
                _message.value = "Playlist'e eklendi"
            }
            .onFailure { _message.value = it.message ?: "Eklenemedi" }
    }

    fun createAndAdd(title: String, songId: Int) = viewModelScope.launch {
        if (title.isBlank()) return@launch
        repo.createPlaylist(title.trim())
            .onSuccess { pl ->
                _playlists.value = listOf(pl) + _playlists.value
                addSong(pl.id, songId)
            }
            .onFailure { _message.value = it.message ?: "Oluşturulamadı" }
    }

    fun clearMessage() { _message.value = null }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddToPlaylistSheet(
    song: SongDto,
    onDismiss: () -> Unit,
    viewModel: AddToPlaylistViewModel = hiltViewModel(),
) {
    val playlists by viewModel.playlists.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val addedIds by viewModel.addedIds.collectAsState()
    val message by viewModel.message.collectAsState()
    val c = Musiki.colors

    LaunchedEffect(Unit) { viewModel.load() }

    message?.let {
        LaunchedEffect(it) {
            kotlinx.coroutines.delay(1500)
            viewModel.clearMessage()
        }
    }

    var showCreate by remember { mutableStateOf(false) }
    var newTitle by remember { mutableStateOf("") }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = c.darkGray,
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "Playlist'e ekle",
                style = MaterialTheme.typography.titleMedium,
                color = c.textPrimary,
            )
            Text(
                song.title,
                style = MaterialTheme.typography.bodySmall,
                color = c.textSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(12.dp))

            if (showCreate) {
                OutlinedTextField(
                    value = newTitle,
                    onValueChange = { newTitle = it },
                    label = { Text("Yeni playlist adı") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = musikiTextFieldColors(),
                )
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { showCreate = false }) { Text("İptal") }
                    Button(
                        onClick = {
                            viewModel.createAndAdd(newTitle, song.id)
                            newTitle = ""
                            showCreate = false
                        },
                        enabled = newTitle.isNotBlank(),
                        colors = ButtonDefaults.buttonColors(containerColor = c.primary),
                    ) { Text("Oluştur ve Ekle") }
                }
            } else {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { showCreate = true }
                        .padding(vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(c.gray),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, tint = c.primary)
                    }
                    Text("Yeni Playlist", color = c.textPrimary)
                }
                HorizontalDivider(color = c.gray, thickness = 0.5.dp)
            }

            message?.let {
                Spacer(Modifier.height(8.dp))
                Text(it, color = c.primary, style = MaterialTheme.typography.bodySmall)
            }

            Spacer(Modifier.height(8.dp))

            when {
                isLoading -> Box(
                    Modifier.fillMaxWidth().padding(24.dp),
                    contentAlignment = Alignment.Center,
                ) { CircularProgressIndicator(color = c.primary) }
                playlists.isEmpty() -> Text(
                    "Henüz playlist yok. Yeni oluştur.",
                    color = c.textSecondary,
                    modifier = Modifier.padding(vertical = 16.dp),
                )
                else -> LazyColumn(modifier = Modifier.heightIn(max = 360.dp)) {
                    items(playlists, key = { it.id }) { pl ->
                        val added = pl.id in addedIds
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable(enabled = !added) { viewModel.addSong(pl.id, song.id) }
                                .padding(vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(c.gray),
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(
                                    Icons.Default.QueueMusic,
                                    contentDescription = null,
                                    tint = c.primary,
                                )
                            }
                            Column(Modifier.weight(1f)) {
                                Text(
                                    pl.title,
                                    color = c.textPrimary,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                Text(
                                    "${pl.item_count} şarkı",
                                    color = c.textSecondary,
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                            if (added) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = "Eklendi",
                                    tint = c.primary,
                                )
                            }
                        }
                        HorizontalDivider(color = c.gray, thickness = 0.5.dp)
                    }
                }
            }
        }
    }
}
