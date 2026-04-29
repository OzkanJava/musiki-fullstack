package com.ozkanilkay.musiki_frontend.ui.library

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.data.repository.MusicRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LikedSongsViewModel @Inject constructor(
    private val repo: MusicRepository,
) : ViewModel() {
    private val _songs = MutableStateFlow<List<SongDto>>(emptyList())
    val songs = _songs.asStateFlow()
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()
    private val _error = MutableStateFlow<String?>(null)
    val error = _error.asStateFlow()

    init { load() }

    fun load() = viewModelScope.launch {
        _isLoading.value = true
        _error.value = null
        repo.getLikedSongs()
            .onSuccess { _songs.value = it }
            .onFailure { _error.value = it.message }
        _isLoading.value = false
    }

    fun unlike(song: SongDto) {
        _songs.update { list -> list.filterNot { it.id == song.id } }
        viewModelScope.launch {
            val result = repo.unlikeSong(song.id)
            if (result.isFailure) load()
        }
    }
}
