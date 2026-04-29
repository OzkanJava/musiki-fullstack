package com.ozkanilkay.musiki_frontend.ui.search

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.player.PlayerViewModel
import com.ozkanilkay.musiki_frontend.ui.components.ArtistCard
import com.ozkanilkay.musiki_frontend.ui.components.SongRow
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki
import androidx.compose.ui.text.input.ImeAction

@Composable
fun SearchScreen(
    playerViewModel: PlayerViewModel,
    onOpenArtist: (Int) -> Unit,
    viewModel: SearchViewModel = hiltViewModel(),
) {
    val query by viewModel.query.collectAsState()
    val results by viewModel.results.collectAsState()
    val artists by viewModel.artists.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val currentSong by playerViewModel.currentSong.collectAsState()
    val isPlaying by playerViewModel.isPlaying.collectAsState()
    val c = Musiki.colors

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(c.background)
            .padding(horizontal = 16.dp),
    ) {
        Spacer(Modifier.height(16.dp))

        OutlinedTextField(
            value = query,
            onValueChange = viewModel::onQueryChange,
            placeholder = { Text("Şarkı, sanatçı ara...") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = c.textSecondary) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor   = c.primary,
                unfocusedBorderColor = c.outline,
                focusedTextColor     = c.textPrimary,
                unfocusedTextColor   = c.textPrimary,
                cursorColor          = c.primary,
            ),
        )

        Spacer(Modifier.height(12.dp))

        when {
            isLoading -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = c.primary)
                }
            }
            query.isBlank() -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Aramak istediğin şarkıyı veya sanatçıyı yaz", color = c.textSecondary)
                }
            }
            results.isEmpty() && artists.isEmpty() -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Sonuç bulunamadı", color = c.textSecondary)
                }
            }
            else -> {
                LazyColumn {
                    if (artists.isNotEmpty()) {
                        item { SectionTitle("Sanatçılar") }
                        item {
                            LazyRow(
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                                contentPadding = PaddingValues(vertical = 8.dp),
                            ) {
                                items(artists, key = { it.id }) { artist ->
                                    ArtistCard(
                                        name = artist.username,
                                        onClick = { onOpenArtist(artist.id) },
                                    )
                                }
                            }
                        }
                        item { Spacer(Modifier.height(8.dp)) }
                    }

                    if (results.isNotEmpty()) {
                        item { SectionTitle("Şarkılar") }
                        itemsIndexed(results, key = { _, s -> s.id }) { index, song ->
                            SongRow(
                                song = song,
                                isCurrentlyPlaying = currentSong?.id == song.id && isPlaying,
                                isCurrentSong = currentSong?.id == song.id,
                                onClick = { playerViewModel.playQueue(results, index) },
                                onArtistClick = onOpenArtist,
                            )
                            HorizontalDivider(
                                color = c.darkGray,
                                thickness = 0.5.dp,
                            )
                        }
                    }

                    item { Spacer(Modifier.height(24.dp)) }
                }
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    val c = Musiki.colors
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        color = c.textPrimary,
        modifier = Modifier.padding(vertical = 8.dp),
    )
}
