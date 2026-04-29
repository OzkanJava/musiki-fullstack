package com.ozkanilkay.musiki_frontend.ui.library

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.local.LocalMusicRepository
import com.ozkanilkay.musiki_frontend.data.model.LocalTrack
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LocalMusicViewModel @Inject constructor(
    private val repo: LocalMusicRepository,
) : ViewModel() {
    private val _tracks = MutableStateFlow<List<LocalTrack>>(emptyList())
    val tracks = _tracks.asStateFlow()
    private val _isLoading = MutableStateFlow(false)
    val isLoading = _isLoading.asStateFlow()
    private val _hasPermission = MutableStateFlow(false)
    val hasPermission = _hasPermission.asStateFlow()

    fun onPermissionGranted() {
        _hasPermission.value = true
        refresh()
    }

    fun refresh() = viewModelScope.launch {
        _isLoading.value = true
        _tracks.value = repo.scanDeviceAudio()
        _isLoading.value = false
    }
}
