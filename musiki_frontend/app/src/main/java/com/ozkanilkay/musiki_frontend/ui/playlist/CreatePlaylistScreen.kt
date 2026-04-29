package com.ozkanilkay.musiki_frontend.ui.playlist

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki
import com.ozkanilkay.musiki_frontend.ui.theme.musikiTextFieldColors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreatePlaylistScreen(
    onBack: () -> Unit,
    onCreated: () -> Unit,
    viewModel: CreatePlaylistViewModel = hiltViewModel(),
) {
    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    val isCreating by viewModel.isCreating.collectAsState()
    val error by viewModel.error.collectAsState()
    val c = Musiki.colors

    Scaffold(
        containerColor = c.background,
        topBar = {
            TopAppBar(
                title = { Text("Yeni Playlist", color = c.textPrimary) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Geri", tint = c.textPrimary)
                    }
                },
                windowInsets = WindowInsets(0),
                colors = TopAppBarDefaults.topAppBarColors(containerColor = c.background),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            OutlinedTextField(
                value = title,
                onValueChange = { title = it },
                label = { Text("Başlık") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = musikiTextFieldColors(),
            )
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = { Text("Açıklama (opsiyonel)") },
                modifier = Modifier.fillMaxWidth().height(120.dp),
                shape = RoundedCornerShape(12.dp),
                colors = musikiTextFieldColors(),
            )
            error?.let { Text(it, color = c.error) }
            Button(
                onClick = { viewModel.create(title, description) { onCreated() } },
                enabled = !isCreating,
                colors = ButtonDefaults.buttonColors(containerColor = c.primary),
                modifier = Modifier.fillMaxWidth().height(48.dp),
            ) {
                if (isCreating) CircularProgressIndicator(color = c.onPrimary, modifier = Modifier.size(20.dp))
                else Text("Oluştur")
            }
        }
    }
}
