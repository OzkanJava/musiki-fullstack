package com.ozkanilkay.musiki_frontend.ui.theme

import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.runtime.Composable

@Composable
fun musikiTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor   = Musiki.colors.primary,
    unfocusedBorderColor = Musiki.colors.outline,
    focusedLabelColor    = Musiki.colors.primary,
    unfocusedLabelColor  = Musiki.colors.textSecondary,
    cursorColor          = Musiki.colors.primary,
    focusedTextColor     = Musiki.colors.textPrimary,
    unfocusedTextColor   = Musiki.colors.textPrimary,
)
