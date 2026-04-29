package com.ozkanilkay.musiki_frontend.ui.playlist

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.PlaylistDetailDto
import com.ozkanilkay.musiki_frontend.data.model.PlaylistDto
import com.ozkanilkay.musiki_frontend.data.repository.PlaylistRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class PlaylistListViewModel @Inject constructor(
    private val repo: PlaylistRepository,
) : ViewModel() {
    private val _playlists = MutableStateFlow<List<PlaylistDto>>(emptyList())
    val playlists = _playlists.asStateFlow()
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()

    init { load() }

    fun load() = viewModelScope.launch {
        _isLoading.value = true
        repo.getPlaylists().onSuccess { _playlists.value = it }
        _isLoading.value = false
    }

    fun delete(id: Int) {
        _playlists.update { list -> list.filterNot { it.id == id } }
        viewModelScope.launch {
            val r = repo.delete(id)
            if (r.isFailure) load()
        }
    }
}

@HiltViewModel
class CreatePlaylistViewModel @Inject constructor(
    private val repo: PlaylistRepository,
) : ViewModel() {
    private val _isCreating = MutableStateFlow(false)
    val isCreating = _isCreating.asStateFlow()
    private val _error = MutableStateFlow<String?>(null)
    val error = _error.asStateFlow()

    fun create(title: String, description: String, onSuccess: () -> Unit) {
        if (title.isBlank()) { _error.value = "Başlık boş olamaz"; return }
        _isCreating.value = true
        _error.value = null
        viewModelScope.launch {
            repo.createPlaylist(title.trim(), description.trim())
                .onSuccess { onSuccess() }
                .onFailure { _error.value = it.message }
            _isCreating.value = false
        }
    }
}

@HiltViewModel
class PlaylistDetailViewModel @Inject constructor(
    private val repo: PlaylistRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val playlistId: Int = savedStateHandle.get<Int>("id") ?: error("playlist id missing")

    private val _detail = MutableStateFlow<PlaylistDetailDto?>(null)
    val detail = _detail.asStateFlow()
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()

    init { load() }

    fun load() = viewModelScope.launch {
        _isLoading.value = true
        repo.getDetail(playlistId).onSuccess { _detail.value = it }
        _isLoading.value = false
    }

    fun removeItem(itemId: Int) {
        _detail.update { d ->
            d?.copy(items = d.items.filterNot { it.id == itemId })
        }
        viewModelScope.launch {
            val r = repo.removeItem(playlistId, itemId)
            if (r.isFailure) load()
        }
    }
}
