package com.ozkanilkay.musiki_frontend.ui.detail

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.AlbumDetailDto
import com.ozkanilkay.musiki_frontend.data.repository.MusicRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AlbumDetailViewModel @Inject constructor(
    private val repo: MusicRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val albumId: Int = savedStateHandle.get<Int>("id") ?: error("album id missing")

    private val _album = MutableStateFlow<AlbumDetailDto?>(null)
    val album = _album.asStateFlow()
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()
    private val _error = MutableStateFlow<String?>(null)
    val error = _error.asStateFlow()

    init { load() }

    fun load() = viewModelScope.launch {
        _isLoading.value = true
        _error.value = null
        repo.getAlbumDetail(albumId)
            .onSuccess { _album.value = it }
            .onFailure { _error.value = it.message }
        _isLoading.value = false
    }

    fun toggleSongLike(songId: Int) {
        val current = _album.value ?: return
        val newLiked = current.songs.firstOrNull { it.id == songId }?.is_liked?.not() ?: return
        _album.update { d ->
            d?.copy(songs = d.songs.map { if (it.id == songId) it.copy(is_liked = newLiked) else it })
        }
        viewModelScope.launch {
            val r = if (newLiked) repo.likeSong(songId) else repo.unlikeSong(songId)
            if (r.isFailure) {
                _album.update { d ->
                    d?.copy(songs = d.songs.map { if (it.id == songId) it.copy(is_liked = !newLiked) else it })
                }
            }
        }
    }
}
