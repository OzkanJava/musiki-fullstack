package com.ozkanilkay.musiki_frontend.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.ArtistListItemDto
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.data.repository.MusicRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val musicRepository: MusicRepository,
) : ViewModel() {

    private val _recentlyPlayed = MutableStateFlow<List<SongDto>>(emptyList())
    val recentlyPlayed = _recentlyPlayed.asStateFlow()

    private val _forYou = MutableStateFlow<List<SongDto>>(emptyList())
    val forYou = _forYou.asStateFlow()

    private val _artists = MutableStateFlow<List<ArtistListItemDto>>(emptyList())
    val artists = _artists.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error = _error.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            val recent = async { musicRepository.getRecentlyPlayed() }
            val foryou = async { musicRepository.getForYou() }
            val artistsCall = async { musicRepository.getArtists() }

            recent.await().onSuccess { _recentlyPlayed.value = it }
            foryou.await().onSuccess { _forYou.value = it }
            artistsCall.await()
                .onSuccess { _artists.value = it }
                .onFailure { _error.value = it.message }

            _isLoading.value = false
        }
    }

    fun setLiked(songId: Int, liked: Boolean) {
        val update: (SongDto) -> SongDto = { s ->
            if (s.id == songId) s.copy(is_liked = liked) else s
        }
        _recentlyPlayed.update { it.map(update) }
        _forYou.update { it.map(update) }
    }

    fun toggleLike(song: SongDto) {
        val newLiked = !song.is_liked
        setLiked(song.id, newLiked)
        viewModelScope.launch {
            val result = if (newLiked) musicRepository.likeSong(song.id)
                         else musicRepository.unlikeSong(song.id)
            if (result.isFailure) {
                setLiked(song.id, !newLiked)
            }
        }
    }
}
