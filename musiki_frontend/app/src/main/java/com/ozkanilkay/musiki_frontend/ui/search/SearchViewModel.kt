package com.ozkanilkay.musiki_frontend.ui.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.ArtistListItemDto
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.data.repository.MusicRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@OptIn(FlowPreview::class)
@HiltViewModel
class SearchViewModel @Inject constructor(
    private val musicRepository: MusicRepository,
) : ViewModel() {

    private val _query = MutableStateFlow("")
    val query = _query.asStateFlow()

    private val _results = MutableStateFlow<List<SongDto>>(emptyList())
    val results = _results.asStateFlow()

    private val _artists = MutableStateFlow<List<ArtistListItemDto>>(emptyList())
    val artists = _artists.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()

    init {
        viewModelScope.launch {
            _query
                .debounce(300)
                .collectLatest { q ->
                    if (q.isBlank()) {
                        _results.value = emptyList()
                        _artists.value = emptyList()
                        return@collectLatest
                    }
                    _isLoading.value = true
                    val songsDeferred = async { musicRepository.searchSongs(q) }
                    val artistsDeferred = async { musicRepository.getArtists(search = q) }
                    songsDeferred.await()
                        .onSuccess { _results.value = it }
                        .onFailure { _results.value = emptyList() }
                    artistsDeferred.await()
                        .onSuccess { _artists.value = it }
                        .onFailure { _artists.value = emptyList() }
                    _isLoading.value = false
                }
        }
    }

    fun onQueryChange(q: String) {
        _query.value = q
    }
}
