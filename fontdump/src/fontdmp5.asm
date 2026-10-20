; SPDX-License-Identifier: GPL-3.0-only
; Copyright (C) 2026 Lee Matthew Jackson - PcW16ers.net & leematthewjackson.com
; ============================================================================
; FONTDMP5 -- FONTDUMP Stage 3b: the glyphs FONTDMP4 did not cover
; ============================================================================
; Part of PcW16 Typeface Preservation (see ../../README.md). Writes
; FD5<face><size>.FD5 files (docs/FORMAT.md, version 5). XAnne-verified for
; Times, Times Bold and Swiss; FONTCAP.PRG is the general successor.
;
; FONTDMP4 (XAnne runs 4, 5) captured codes 20-CF. This program is the same
; program -- font selection, guarded os_typo_init, menu, resumable files,
; W/K renders, bios_getpxl capture, rect sizing -- with a different
; character list, and the ACCENT passed in B to os_typo_charinfo and
; os_typo_charscreen (ROSAN283: "C = Character number, B = accent (0 if
; none)"):
;   pass 1  single codes 01-1F and D0-FF, no accent: the accents themselves
;           (D0-DF) and whatever Rosanne draws for the codes ROSAN283
;           reserves for controls (undefined ones: charinfo A=5, header only)
;   pass 2  every accent D0-DF over every base ROSAN283 allows accents on:
;           space, A-Z, a-z, the diphthongs 91-94 and the O-slashes 9B, 9D
;           (Appendix "Accents"): 16 x 59 = 944 combinations.
; Rosanne positions the accent itself ("height above the baseline is
; automatically adjusted"; i/j lose their dot), so each combination is
; captured exactly as Rosanne draws it.
;
; Capture margins grow with the size (3 + size/8 px each side, 2 + size/4
; rows above and below): accents can overhang narrow letters (circumflex over i) and
; under-accents on descenders reach below the font's maximum descender.
;
; Everything else is FONTDMP4's (src/fontdmp4.asm), unchanged; see its
; header for the verified facts it relies on and its safety rules.
;
; Build: build.sh (pasmo --bin src/fontdmp5.asm build/FONTDMP5.PRG).
; ============================================================================

OS              equ 003Bh
B_GETMEM0       equ 0C8h
B_GETMEM1       equ 0CBh
B_GETMEM2       equ 0CEh
B_GETMEM3       equ 0D1h
B_SETMEM2       equ 0C2h
B_GETTIME       equ 0B0h        ; BIOS #10: E ticks, D s, C min, B h
B_SETINK        equ 0E0h
B_GETINK        equ 0E3h
B_SETMODE       equ 0E6h
B_GETMODE       equ 0E9h
B_GETPXL        equ 0F5h

F_APP_EXIT      equ 23
F_COPY24        equ 41
F_ALERT         equ 76
F_TYPO_INIT     equ 83
F_TYPO_GETLIST  equ 84
F_TYPO_SELECT   equ 85
F_TYPO_GETSEL   equ 86
F_TYPO_DEF      equ 87
F_TYPO_CLR      equ 88
F_TYPO_INFO     equ 90
F_TYPO_CHARINFO equ 92
F_TYPO_CHARSCR  equ 93
F_MOUSE_OFF     equ 111
F_MOUSE_ON      equ 112
F_SCR_DIRECT    equ 117
F_SCR_WINDOW    equ 118
F_SCR_GETWINDOW equ 119
F_OPEN          equ 144
F_CLOSE         equ 145
F_WRITE         equ 146

DG_WHITE        equ 1
DG_BLACK        equ 2

; drawing area (clip window) and glyph origin
AX              equ 112
AY              equ 64
AW              equ 288
AH              equ 192
GX              equ 160
GY              equ 200         ; room for ~81 rows above, ~22 below
MARGIN_X        equ 3           ; base margins; FONTDMP5 adds size/8 across, size/4 rows
MARGIN_Y        equ 2           ; (accents can overhang narrow letters, and
                                ; under-accents on descenders go below the
                                ; font's max descender): cf_mx, cf_my
SAFE_UPP        equ 22          ; units per pixel used to size rects
MAX_ROWB        equ 14
MAX_H           equ 144
BUFN            equ MAX_ROWB*MAX_H
ACC_FIRST       equ 0D0h
ACC_LAST        equ 0DFh

MAX_FONTS       equ 20
FONT_REC        equ 37
LDATA           equ MAX_FONTS*FONT_REC
L_COPY          equ 8
L_MAP           equ 8+LDATA
LREC            equ 8+2*LDATA
GH_LEN          equ 28          ; GLY4 header

LOW_NAME        equ 2100h
LOW_EXT         equ 2120h
LOW_DG          equ 2200h
LOW_WIN         equ 2220h

    org 4000h
    defs 100h

; ============================================================================
start:
    call B_GETMEM1
    ld (app_bank),a
    ld hl,lst1
    call list_read              ; first OS call, as FONTDMP2/3
    call B_GETINK
    ld (env_ink),a
    call B_GETMODE
    ld (env_mode),a
    ld a,F_TYPO_GETSEL
    call OS
    ld a,e
    ld (env_slot),a
    ld a,F_SCR_GETWINDOW
    call OS
    ld de,env_win
    ld ix,8
    call fd_copy24
    push af
    pop hl
    ld a,l
    ld (env_win_f),a

    ; ---- menu --------------------------------------------------------------
    ld hl,menu_def
    ld de,menu_len
    ld a,(app_bank)
    ld c,a
    ld a,F_ALERT
    call OS
    jp c,exit                   ; refused: nothing touched
    cp 2
    jp nc,exit                  ; Cancel (or Stop)
    ld (menu_choice),a          ; 0 = 12pt only, 1 = all sizes

    ; ---- slot survey -------------------------------------------------------
    xor a
    ld (sv_e),a
slot_survey:
    ld a,(sv_e)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld c,a
    ld a,(sv_e)
    ld e,a
    ld d,0
    ld hl,slot_tab
    add hl,de
    ld (hl),c
    inc a
    ld (sv_e),a
    cp 16
    jp nz,slot_survey
    ld hl,slot_tab+1
    ld b,15
    ld c,1
slot_pick:
    ld a,(hl)
    cp 4
    jp z,slot_found
    inc hl
    inc c
    djnz slot_pick
    ld a,(slot_tab)
    cp 4
    jp nz,no_slot
    ld c,0
slot_found:
    ld a,c
    ld (slot_use),a
    ld hl,slot_tab
    ld b,16
    ld a,1
    ld (all_empty),a
slot_empty_chk:
    ld a,(hl)
    cp 4
    jp z,slot_empty_next
    xor a
    ld (all_empty),a
slot_empty_next:
    inc hl
    djnz slot_empty_chk

    ; ---- fonts, test definition, guarded init ------------------------------
    ld hl,lst1
    ld (lst_cur),hl
    call find_faces
    call test_def
    jp z,fonts_ok
    ld a,(all_empty)
    or a
    jp z,fonts_ok               ; cannot init safely: faces will fail
    ld a,F_TYPO_INIT
    call OS
    push af
    pop hl
    ld a,l
    ld (init_f),a
    ld a,1
    ld (init_done),a
    ld hl,lst2
    call list_read
    ld hl,lst2
    ld (lst_cur),hl
    call find_faces
    call test_def
fonts_ok:

    ; ==== the drawing area ===================================================
    ld a,F_MOUSE_OFF
    call OS
    xor a
    call B_SETINK
    xor a
    call B_SETMODE
    ld hl,area_rect
    call fd_window
    ld hl,area_rect
    ld a,DG_WHITE
    call fd_dg

    ; ==== sizes x faces ======================================================
    ld hl,size_tab
    ld (sz_ptr),hl
size_loop:
    ld hl,(sz_ptr)
    ld a,(hl)
    or a
    jp z,all_done
    inc hl
    ld (sz_ptr),hl
    ld (cur_size),a
    xor a
    ld (cur_face),a
face_loop:
    call do_combo
    ld a,(cur_face)
    inc a
    ld (cur_face),a
    cp 3
    jp nz,face_loop
    ld a,(menu_choice)
    or a
    jp z,all_done               ; 12pt only: the first table entry
    jp size_loop
all_done:
    call fd_window_restore
    ld a,(env_mode)
    call B_SETMODE
    ld a,(env_ink)
    call B_SETINK
    ld a,F_MOUSE_ON
    call OS
    ld a,(env_slot)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    call show_summary
exit:
    ld a,F_APP_EXIT
    call OS
    ret

no_slot:
    ld a,(env_slot)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld de,al_text
    ld hl,t_noslot
    call al_puts
    call al_show
    jp exit

; ============================================================================
; one face at one size
; ============================================================================
do_combo:
    ; face parameters: family, style, code
    ld a,(cur_face)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl                   ; 4 bytes per face_tab entry
    ld de,face_tab
    add hl,de
    ld a,(hl)
    ld (cf_family),a
    inc hl
    ld a,(hl)
    ld (cf_style),a
    inc hl
    ld a,(hl)
    ld (stem+3),a
    inc hl
    ld a,(hl)
    ld (stem+4),a
    ld a,(cur_size)             ; three decimal digits
    ld c,'0'-1
dc_h:
    inc c
    sub 100
    jp nc,dc_h
    add a,100
    ld b,a
    ld a,c
    ld (stem+5),a
    ld a,b
    ld c,'0'-1
dc_t:
    inc c
    sub 10
    jp nc,dc_t
    add a,10+'0'
    ld (stem+7),a
    ld a,c
    ld (stem+6),a
    ; the face's list entry
    ld a,(cf_family)
    cp 1
    ld hl,(times_ptr)
    jp z,dc_have
    ld hl,(swiss_ptr)
dc_have:
    ld a,h
    or l
    jp z,dc_missing
    ld (cf_entry),hl
    inc hl
    inc hl
    ld a,(hl)                   ; styles
    or 1
    ld (cf_styles),a
    ld a,(cf_style)
    or a
    jp z,dc_style_ok
    ld a,(cf_styles)
    and 2
    jp z,dc_missing             ; no Bold style in this family
dc_style_ok:
    ; skip if the file exists
    ld hl,ext_fd5
    call fd_exists
    jp nz,dc_skip
    ; define
    ld a,(slot_use)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld hl,(cf_entry)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,(cf_styles)
    ld d,a
    ld a,(cur_size)
    ld b,a
    ld a,F_TYPO_DEF
    call OS
    ld (cf_def_a),a
    push af
    pop hl
    ld a,l
    ld (cf_def_f),a
    ld a,(cf_def_a)
    or a
    jp nz,dc_fail_def
    ; margins for this size: 3 + size/8 px across, 2 + size/4 rows above
    ; and below (72pt: 12 px, 20 rows; the 72pt rect is then 13 bytes x
    ; 141 rows, inside MAX_ROWB x MAX_H and the drawing area)
    ld a,(cur_size)
    srl a
    srl a
    ld b,a
    add a,MARGIN_Y
    ld (cf_my),a
    ld a,b
    srl a
    add a,MARGIN_X
    ld (cf_mx),a
    ; metrics for the rect height
    ld a,F_TYPO_INFO
    call OS
    ld (info_a),a
    ld (info_hl),hl
    or a
    jp nz,dc_noinfo
    ld a,h
    cp 40h
    jp nc,dc_noinfo
    ld de,info_data
    ld bc,8
    ldir
dc_noinfo:
    ld hl,(info_data+2)         ; max ascender
    call div22c
    ld hl,cf_my
    add a,(hl)
    ld (rect_asc),a
    ld hl,(info_data+4)         ; max descender
    call div22c
    ld hl,cf_my
    add a,(hl)
    ld b,a
    ld a,(rect_asc)
    add a,b
    ld (rect_h),a
    ld a,0
    ld (rect_flags),a
    ld a,(rect_h)
    cp MAX_H+1
    jp c,dc_h_ok
    ld a,MAX_H
    ld (rect_h),a
    ld a,1
    ld (rect_flags),a
dc_h_ok:
    ld a,(rect_asc)
    ld e,a
    ld d,0
    ld hl,GY
    or a
    sbc hl,de
    ld (cr_y),hl
    ; file
    ld hl,ext_fd5
    call fd_open
    jp c,dc_fail_open
    ld hl,hdr_fd5
    ld de,8
    call fd_raw
    ld a,5
    ld (hdr_var),a              ; version
    ld a,3
    ld (hdr_var+1),a            ; stage
    ld a,(cur_face)
    ld (hdr_var+2),a
    ld a,(cur_size)
    ld (hdr_var+3),a
    ld hl,(cf_entry)
    ld a,(hl)
    ld (hdr_var+4),a
    inc hl
    ld a,(hl)
    ld (hdr_var+5),a
    ld a,(cf_styles)
    ld (hdr_var+6),a
    ld a,(cf_style)
    ld (hdr_var+7),a
    ld hl,hdr_var
    ld de,8
    call fd_raw
    ; FACE: list entry, def A/F, init flags
    ld hl,(cf_entry)
    ld de,face_rec
    ld bc,FONT_REC
    ldir
    ld a,(cf_def_a)
    ld (face_rec+37),a
    ld a,(cf_def_f)
    ld (face_rec+38),a
    ld a,(init_done)
    ld (face_rec+39),a
    ld a,(init_f)
    ld (face_rec+40),a
    ld a,(slot_use)
    ld (face_rec+41),a
    ld a,(lst_src)
    ld (face_rec+42),a
    ld hl,tag_face
    ld de,43
    ld bc,face_rec
    call fd_record
    ld hl,tag_info
    ld de,11
    ld bc,info_a
    call fd_record
    call B_GETTIME
    ld (tim_buf),de
    ld (tim_buf+2),bc
    ld hl,tag_tim0
    ld de,4
    ld bc,tim_buf
    call fd_record
    ; characters: pass 1 single codes, pass 2 accent x base
    ld hl,0
    ld (cf_glyphs),hl
    xor a
    ld (cur_acc),a
    ld hl,single_tab
    ld (ct_ptr),hl
sg_loop:
    ld hl,(ct_ptr)
    ld a,(hl)
    or a
    jp z,sg_done
    inc hl
    ld (ct_ptr),hl
    ld (cur_ch),a
    call do_glyph
    jp sg_loop
sg_done:
    ld a,ACC_FIRST
    ld (cur_acc),a
ac_loop:
    ld hl,base_tab
    ld (ct_ptr),hl
ab_loop:
    ld hl,(ct_ptr)
    ld a,(hl)
    or a
    jp z,ab_done
    inc hl
    ld (ct_ptr),hl
    ld (cur_ch),a
    call do_glyph
    jp ab_loop
ab_done:
    ld a,(cur_acc)
    cp ACC_LAST
    jp z,ch_done
    inc a
    ld (cur_acc),a
    jp ac_loop
ch_done:
    call B_GETTIME
    ld (tim_buf),de
    ld (tim_buf+2),bc
    ld hl,tag_tim1
    ld de,4
    ld bc,tim_buf
    call fd_record
    ld hl,tag_end
    ld de,0
    ld bc,0
    call fd_record
    call fd_close
    ; release the slot
    ld a,(slot_use)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld a,F_TYPO_CLR
    call OS
    ld a,(wr_err)
    or a
    jp nz,dc_fail_write
    ld hl,n_done
    inc (hl)
    ld hl,stem
    ld de,last_done
    ld bc,9
    ldir
    ret
dc_skip:
    ld hl,n_skip
    inc (hl)
    ret
dc_missing:
    ld hl,n_missing
    inc (hl)
    ret
dc_fail_def:
    ld a,(cf_def_a)
    ld (fail_code),a
    ld a,'D'
    jp dc_fail
dc_fail_open:
    ld a,(slot_use)             ; release the slot defined above
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    ld a,F_TYPO_CLR
    call OS
    ld a,(wr_err)
    ld (fail_code),a
    ld a,'O'
    jp dc_fail
dc_fail_write:
    ld a,(wr_err)
    ld (fail_code),a
    ld a,'W'
dc_fail:
    ld (fail_kind),a
    ld hl,n_fail
    inc (hl)
    ld hl,stem
    ld de,last_fail
    ld bc,9
    ldir
    ret

; ============================================================================
; one glyph: charinfo, W and K renders, GLY4 record
; ============================================================================
do_glyph:
    ld hl,gh
    ld b,GH_LEN
dg_clear:
    ld (hl),0
    inc hl
    djnz dg_clear
    ld a,(cur_ch)
    ld (gh+0),a
    ld a,(cur_acc)
    ld (gh+1),a
    ld a,(cf_style)
    ld (gh+2),a
    ld a,0FFh
    ld (gh+11),a
    ld (gh+12),a
    ld hl,GX
    ld (gh+14),hl
    ld hl,GY
    ld (gh+16),hl
    ; os_typo_charinfo (D = style: bit 0 bold)
    ld a,(cur_acc)
    ld b,a                      ; accent (0 = none)
    ld a,(cur_ch)
    ld c,a
    ld a,(cf_style)
    ld d,a
    ld a,F_TYPO_CHARINFO
    call OS
    ld (gh+5),de
    ld (gh+7),hl
    ld (gh+9),bc
    push af
    pop hl
    ld a,h
    ld (gh+3),a
    ld a,l
    ld (gh+4),a
    ld a,h
    or a
    jp nz,gl_header_only        ; undefined character: metrics only
    ; rect: x from GX-3, width ceil(w/22)+6 rounded up to bytes
    ld hl,(gh+5)
    call div22c
    ld hl,cf_mx                 ; width ceil(w/22) + 2 margins, rounded up to bytes
    add a,(hl)
    add a,(hl)
    add a,7
    srl a
    srl a
    srl a                       ; bytes per row
    cp MAX_ROWB+1
    jp c,gl_rowb_ok
    ld a,(rect_flags)
    or 2
    ld (rect_flags),a
    ld a,MAX_ROWB
gl_rowb_ok:
    ld (cr_rowb),a
    ld (gh+26),a
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld (gh+22),hl               ; rect width in pixels
    ld a,(cf_mx)
    ld e,a
    ld d,0
    ld hl,GX
    or a
    sbc hl,de
    ld (cr_x),hl
    ld (gh+18),hl
    ld hl,(cr_y)
    ld (gh+20),hl
    ld a,(rect_h)
    ld (cr_h),a
    ld l,a
    ld h,0
    ld (gh+24),hl
    ld a,(rect_flags)
    ld (gh+13),a
    ; capture size = rowb * h
    ld a,(cr_rowb)
    ld e,a
    ld d,0
    ld hl,0
    ld a,(rect_h)
    ld b,a
gl_mul:
    add hl,de
    djnz gl_mul
    ld (cap_len),hl
    ; dg rect = x, y, w, h
    ld hl,(gh+18)
    ld (dg_rect),hl
    ld hl,(gh+20)
    ld (dg_rect+2),hl
    ld hl,(gh+22)
    ld (dg_rect+4),hl
    ld hl,(gh+24)
    ld (dg_rect+6),hl
    ; W render
    ld hl,dg_rect
    ld a,DG_WHITE
    call fd_dg
    call gl_draw
    ld (gh+11),a
    ld hl,buf_w
    call cap_rect
    ; K render
    ld hl,dg_rect
    ld a,DG_BLACK
    call fd_dg
    call gl_draw
    ld (gh+12),a
    ld hl,buf_k
    call cap_rect
    ; record: tag, length = header + 2 captures
    ld hl,(cap_len)
    add hl,hl
    ld de,GH_LEN
    add hl,de
    ld (rec_hdr+4),hl
    call gl_tag
    ld hl,gh
    ld de,GH_LEN
    call fd_raw
    ld hl,buf_w
    ld de,(cap_len)
    call fd_raw
    ld hl,buf_k
    ld de,(cap_len)
    call fd_raw
    jp gl_counted
gl_header_only:
    ld hl,GH_LEN
    ld (rec_hdr+4),hl
    call gl_tag
    ld hl,gh
    ld de,GH_LEN
    call fd_raw
gl_counted:
    ld hl,(cf_glyphs)
    inc hl
    ld (cf_glyphs),hl
    ret

gl_tag:
    ld hl,tag_gly4
    ld de,rec_hdr
    ld bc,4
    ldir
    ld hl,rec_hdr
    ld de,6
    jp fd_raw

; gl_draw -- os_typo_charscreen of cur_ch with accent cur_acc at (GX,GY),
; opaque, cf_style.
; out: A = result
gl_draw:
    ld a,(cf_style)
    ld l,a
    ld h,0                      ; IX hi = mode 0 opaque
    push hl
    pop ix
    ld a,(cur_acc)
    ld b,a                      ; accent (0 = none)
    ld a,(cur_ch)
    ld c,a
    ld de,GX
    ld hl,GY
    ld a,F_TYPO_CHARSCR
    call OS
    ret

; cap_rect -- bios_getpxl capture of cr_x, cr_y, cr_rowb bytes x cr_h rows
; into HL: row-major, bit 7 leftmost, 1 = white.
cap_rect:
    ld (cp_dst),hl
    xor a
    ld (cp_y),a
cr_row:
    ld hl,(cr_x)
    ld (cp_px),hl
    ld a,(cr_rowb)
    ld (cp_nb),a
cr_byte:
    ld c,0
    ld b,8
cr_bit:
    push bc
    ld de,(cp_px)
    ld a,(cp_y)
    ld l,a
    ld h,0
    ld bc,(cr_y)
    add hl,bc
    call B_GETPXL
    pop bc
    and 1
    sla c
    or c
    ld c,a
    ld hl,(cp_px)
    inc hl
    ld (cp_px),hl
    djnz cr_bit
    ld hl,(cp_dst)
    ld (hl),c
    inc hl
    ld (cp_dst),hl
    ld a,(cp_nb)
    dec a
    ld (cp_nb),a
    jp nz,cr_byte
    ld a,(cp_y)
    inc a
    ld (cp_y),a
    ld hl,cr_h
    cp (hl)
    jp nz,cr_row
    ret

; div22c -- A = ceil(HL / SAFE_UPP) (HL <= 5600)
div22c:
    ld c,0
d22_loop:
    ld a,h
    or l
    jp z,d22_done
    inc c
    ld de,SAFE_UPP
    or a
    sbc hl,de
    jp nc,d22_loop
d22_done:
    ld a,c
    ret

; ============================================================================
; fonts
; ============================================================================
; find_faces -- times_ptr / swiss_ptr = first valid entry of RTF family 1 / 2
; in the list block at lst_cur: the os_copy_24bit copy, else the mapped read.
; lst_src = 'C', 'M' or 0 (neither valid).
find_faces:
    ld hl,0
    ld (times_ptr),hl
    ld (swiss_ptr),hl
    xor a
    ld (lst_src),a
    ld hl,(lst_cur)
    ld de,L_COPY
    add hl,de
    call scan_list
    ld a,(times_ptr+1)
    or a
    jp nz,ff_copy
    ld a,(swiss_ptr+1)
    or a
    jp nz,ff_copy
    ld hl,(lst_cur)
    ld de,L_MAP
    add hl,de
    call scan_list
    ld a,(times_ptr+1)
    ld b,a
    ld a,(swiss_ptr+1)
    or b
    ret z
    ld a,'M'
    ld (lst_src),a
    ret
ff_copy:
    ld a,'C'
    ld (lst_src),a
    ret

; scan_list -- HL = first entry; uses n at lst_cur+5
scan_list:
    push hl
    ld hl,(lst_cur)
    ld de,5
    add hl,de
    ld b,(hl)
    pop hl
    ld a,b
    or a
    ret z
sl_loop:
    call pf_valid
    jp nz,sl_next
    push hl
    inc hl
    inc hl
    inc hl
    ld a,(hl)                   ; RTF family
    pop hl
    cp 1
    jp nz,sl_not_times
    ld a,(times_ptr+1)
    or a
    jp nz,sl_next
    ld (times_ptr),hl
    jp sl_next
sl_not_times:
    cp 2
    jp nz,sl_next
    ld a,(swiss_ptr+1)
    or a
    jp nz,sl_next
    ld (swiss_ptr),hl
sl_next:
    ld de,FONT_REC
    add hl,de
    djnz sl_loop
    ret

; test_def -- define Times (else Swiss) 12pt in slot_use, record, clear.
; out: Z if it succeeded.
test_def:
    ld hl,(times_ptr)
    ld a,h
    or l
    jp nz,td_have
    ld hl,(swiss_ptr)
    ld a,h
    or l
    jp nz,td_have
    ld hl,fb_entry              ; no valid list: Times ID #0100 (run 1/2)
td_have:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld a,(hl)
    or 1
    push de
    push af
    ld a,(slot_use)
    ld e,a
    ld a,F_TYPO_SELECT
    call OS
    pop af
    ld d,a
    pop hl
    ld b,12
    ld a,F_TYPO_DEF
    call OS
    ld (test_a),a
    or a
    jp nz,td_out
    ld a,F_TYPO_CLR
    call OS
td_out:
    ld a,(test_a)
    or a
    ret

; ============================================================================
; summary
; ============================================================================
show_summary:
    ld de,al_text
    ld hl,t_sum1
    call al_puts
    ld a,(n_done)
    call al_hex
    ld hl,t_skip
    call al_puts
    ld a,(n_skip)
    call al_hex
    ld hl,t_fail
    call al_puts
    ld a,(n_fail)
    call al_hex
    ld hl,t_miss
    call al_puts
    ld a,(n_missing)
    call al_hex
    call al_show
    ld de,al_text
    ld hl,t_sum2
    call al_puts
    ld a,(test_a)
    call al_hex
    ld hl,t_init
    call al_puts
    ld a,(init_f)
    call al_hex
    ld hl,t_src
    call al_puts
    ld a,(lst_src)
    or a
    jp nz,ss_src
    ld a,'-'
ss_src:
    ld (de),a
    inc de
    ld hl,t_last
    call al_puts
    ld hl,last_done
    call al_puts
    call al_show
    ld a,(n_fail)
    or a
    ret z
    ld de,al_text
    ld hl,t_lastfail
    call al_puts
    ld hl,last_fail
    call al_puts
    ld a,' '
    ld (de),a
    inc de
    ld a,(fail_kind)
    ld (de),a
    inc de
    ld a,'='
    ld (de),a
    inc de
    ld a,(fail_code)
    call al_hex
    jp al_show

; ============================================================================
; helpers shared with Stages 1-2, unchanged
; ============================================================================
; fd_exists -- HL = extension text (".FD1",0). out: NZ if FONTDUMP<ext>
; exists (or the probe failed for another reason: safer to refuse), Z if
; os_open_file reported #02 File Not Found.
fd_exists:
    call fd_names
    ld hl,LOW_NAME
    ld de,LOW_EXT
    ld b,0                      ; read mode
    ld a,F_OPEN
    call OS
    jp c,fd_exists_err
    ld b,0
    ld a,F_CLOSE
    call OS
    or 1                        ; NZ: exists
    ret
fd_exists_err:
    cp 2
    ret                         ; Z only for #02

; fd_names -- copy "FONTDUMP",0 to LOW_NAME and the extension at HL to LOW_EXT
fd_names:
    push hl
    ld hl,stem
    ld de,LOW_NAME
    ld bc,9
    ldir
    pop hl
    ld de,LOW_EXT
    ld bc,5
    ldir
    ret

; fd_open -- open FONTDUMP<ext at HL> for write. out: carry = failed
; (wr_err = #80 | ... no: wr_err = OS code, nonzero)
fd_open:
    xor a
    ld (wr_err),a
    call fd_names
    ld hl,LOW_NAME
    ld de,LOW_EXT
    ld b,1
    ld a,F_OPEN
    call OS
    ret nc
    or a
    jp nz,fd_open_code
    ld a,0FFh
fd_open_code:
    ld (wr_err),a
    scf
    ret

; fd_close -- close the write file; a close error is kept unless one is set
fd_close:
    ld b,1
    ld a,F_CLOSE
    call OS
    ret nc
    ld c,a
    ld a,(wr_err)
    or a
    ret nz
    ld a,c
    or a
    jp nz,fd_close_code
    ld a,0FEh
fd_close_code:
    ld (wr_err),a
    ret

; fd_raw -- os_write_file DE bytes from app-bank HL (skipped after an error)
fd_raw:
    ld a,(wr_err)
    or a
    ret nz
    ld a,d
    or e
    ret z
    ld a,(app_bank)
    ld c,a
    ld b,0
    ld a,F_WRITE
    call OS
    ret nc
    or a
    jp nz,fd_raw_code
    ld a,0FDh
fd_raw_code:
    ld (wr_err),a
    ret

; fd_record -- tag at HL (4 bytes), payload length DE, payload address BC
fd_record:
    ld (rec_len),de
    ld (rec_ptr),bc
    ld de,rec_hdr
    ld bc,4
    ldir
    ld hl,(rec_len)
    ld (rec_hdr+4),hl
    ld hl,rec_hdr
    ld de,6
    call fd_raw
    ld hl,(rec_ptr)
    ld de,(rec_len)
    jp fd_raw

; fd_copy24 -- os_copy_24bit IX bytes from C:HL to app-bank DE; F returned
fd_copy24:
    call B_GETMEM1              ; all flags and other registers preserved
    ld b,a
    ld a,F_COPY24
    call OS
    ret

; fd_dg -- os_scr_direct function A on the 8-byte x,y,w,h at HL.
; out: A = F after the call (bit 0 = carry = error, Rosanne 1.12 KI-46)
fd_dg:
    ld (LOW_DG),a
    ld de,LOW_DG+1
    ld bc,8
    ldir
    ld c,80h
    ld hl,LOW_DG
    ld a,F_SCR_DIRECT
    call OS
    push af
    pop hl
    ld a,l
    ret

; fd_window_restore -- put back the window read at start (skipped, A = #FF,
; if that read reported carry)
fd_window_restore:
    ld a,(env_win_f)
    and 1
    ld a,0FFh
    ret nz
    ld hl,env_win
; fd_window -- os_scr_window to the 8-byte x,y,w,h at HL. out: A = F
fd_window:
    ld de,LOW_WIN
    ld bc,8
    ldir
    ld c,80h
    ld hl,LOW_WIN
    ld a,F_SCR_WINDOW
    call OS
    push af
    pop hl
    ld a,l
    ret

; list_read -- os_typo_getlist, then read up to MAX_FONTS entries by
; os_copy_24bit AND by mapping the block at #8000. HL = list-read block.
list_read:
    ld (lr_base),hl
    ld a,F_TYPO_GETLIST
    call OS
    push hl
    ld hl,(lr_base)
    ld (hl),b                   ; +0 count
    inc hl
    ld (hl),c                   ; +1 bank
    inc hl
    pop de
    ld (hl),e                   ; +2 address
    inc hl
    ld (hl),d
    ld a,b
    cp MAX_FONTS+1
    jp c,lr_n_ok
    ld a,MAX_FONTS
lr_n_ok:
    ld hl,(lr_base)
    ld de,5
    add hl,de
    ld (hl),a                   ; +5 n
    or a
    jp nz,lr_have
    inc hl
    inc hl
    ld (hl),3                   ; +7 map status: n = 0
    ret
lr_have:
    ld b,a                      ; lr_len = n * 37
    ld de,FONT_REC
    ld hl,0
lr_mul:
    add hl,de
    djnz lr_mul
    ld (lr_len),hl
    ; (a) os_copy_24bit
    ld hl,(lr_base)
    inc hl
    ld c,(hl)
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    push de
    ld hl,(lr_base)
    ld de,L_COPY
    add hl,de
    ex de,hl                    ; DE = copy destination
    pop hl                      ; HL = source address
    push de
    ld de,(lr_len)
    push de
    pop ix
    pop de
    call fd_copy24
    push af
    pop bc
    ld hl,(lr_base)
    ld de,4
    add hl,de
    ld (hl),c                   ; +4 F
    ; (b) direct read through quarter 2
    call B_GETMEM2
    ld hl,(lr_base)
    ld de,6
    add hl,de
    ld (hl),a                   ; +6 block at #8000 before
    ld hl,(lr_base)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    and 3Fh
    or 80h
    ld d,a                      ; DE = #8000 + (HL AND #3FFF)
    ld (lr_src),de
    ld hl,(lr_len)
    add hl,de                   ; end address
    ld a,h
    cp 0C0h
    jp c,lr_map_ok
    jp nz,lr_map_skip
    ld a,l
    or a
    jp z,lr_map_ok              ; ends exactly at #C000
lr_map_skip:
    ld hl,(lr_base)
    ld de,7
    add hl,de
    ld (hl),2
    ret
lr_map_ok:
    ld hl,(lr_base)
    inc hl
    ld a,(hl)                   ; the list's block
    call B_SETMEM2
    ld hl,(lr_base)
    ld de,L_MAP
    add hl,de
    ex de,hl
    ld hl,(lr_src)
    ld bc,(lr_len)
    ldir
    ld hl,(lr_base)
    ld de,6
    add hl,de
    ld a,(hl)
    call B_SETMEM2              ; put the original block back
    inc hl
    ld (hl),1                   ; +7 map status: read
    ret

; pf_valid -- Z if the entry at HL looks real: ID <> #FFFF and the first
; name character printable. HL, BC preserved.
pf_valid:
    ld a,(hl)
    inc hl
    and (hl)
    dec hl
    cp 0FFh
    jp z,pf_bad
    push hl
    ld de,4
    add hl,de
    ld a,(hl)
    pop hl
    cp 20h
    jp c,pf_bad
    cp 7Fh
    jp nc,pf_bad
    xor a
    ret
pf_bad:
    or 1
    ret

; al_show -- finish the line at DE as an os_alert definition and show it
; (format as WIDTHDG, XAnne-proven: text NUL, extra NUL, 1 button, keys, "OK")
al_show:
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld a,1
    ld (de),a
    inc de
    ld hl,al_keys
    ld bc,11
    ldir
    ld hl,al_text
    ex de,hl
    or a
    sbc hl,de
    ex de,hl                    ; DE = total length
    ld hl,al_text
    ld a,(app_bank)
    ld c,a
    ld a,F_ALERT
    call OS
    ret

; al_puts -- copy NUL-terminated HL to DE (no NUL); DE advanced
al_puts:
    ld a,(hl)
    or a
    ret z
    ld (de),a
    inc hl
    inc de
    jp al_puts

; al_hex -- A as two hex digits at DE
al_hex:
    push af
    rrca
    rrca
    rrca
    rrca
    call al_nib
    pop af
al_nib:
    and 15
    add a,'0'
    cp '9'+1
    jp c,al_nib_out
    add a,7
al_nib_out:
    ld (de),a
    inc de
    ret

; al_dec -- HL as 5 decimal digits at DE
al_dec:
    ld bc,10000
    call al_digit
    ld bc,1000
    call al_digit
    ld bc,100
    call al_digit
    ld bc,10
    call al_digit
    ld bc,1
al_digit:
    ld a,'0'
al_digit_loop:
    or a
    sbc hl,bc
    jp c,al_digit_done
    inc a
    jp al_digit_loop
al_digit_done:
    add hl,bc
    ld (de),a
    inc de
    ret




; ============================================================================
; constant data
; ============================================================================
ext_fd5:    db ".FD5",0
hdr_fd5:    db "P16FONT5"
; pass 1: single codes (0-terminated)
single_tab: db 01h,02h,03h,04h,05h,06h,07h,08h,09h,0Ah,0Bh,0Ch,0Dh,0Eh,0Fh
            db 10h,11h,12h,13h,14h,15h,16h,17h,18h,19h,1Ah,1Bh,1Ch,1Dh,1Eh,1Fh
            db 0D0h,0D1h,0D2h,0D3h,0D4h,0D5h,0D6h,0D7h,0D8h,0D9h,0DAh,0DBh,0DCh,0DDh,0DEh,0DFh
            db 0E0h,0E1h,0E2h,0E3h,0E4h,0E5h,0E6h,0E7h,0E8h,0E9h,0EAh,0EBh,0ECh,0EDh,0EEh,0EFh
            db 0F0h,0F1h,0F2h,0F3h,0F4h,0F5h,0F6h,0F7h,0F8h,0F9h,0FAh,0FBh,0FCh,0FDh,0FEh,0FFh
            db 0
; pass 2: bases accents may go on (ROSAN283 Appendix "Accents"), 0-terminated
base_tab:   db 20h
            db "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            db "abcdefghijklmnopqrstuvwxyz"
            db 91h,92h,93h,94h,9Bh,9Dh
            db 0
tag_face:   db "FACE"
tag_info:   db "INFO"
tag_tim0:   db "TIM0"
tag_tim1:   db "TIM1"
tag_gly4:   db "GLY4"
tag_end:    db "END "
area_rect:  dw AX,AY,AW,AH
; family (RTF), style (charscreen IX lo / charinfo D), file code
face_tab:   db 1,0,"TN"
            db 1,1,"TB"
            db 2,0,"SN"
; 12pt first: the "12pt only" choice stops after it
size_tab:   db 12,6,8,10,11,14,18,24,36,72,0
fb_entry:   dw 0100h
            db 1,1
            db "Times? (fallback ID)",0
; menu: os_alert with 3 buttons (keys as the XAnne-proven ASK: first =
; Return/Green, last = Stop/Red)
menu_def:   db "FONTDMP5: accents and accented letters (944 per font),",0
            db "codes 01-1F, D0-FF. Existing FD5 files skipped. Which sizes?",0
            db 0
            db 3
            dw 800Dh,80FBh,0,0
            db "12pt only",0
            dw 0,0,0,0
            db "All sizes",0
            dw 80FEh,80FCh,0,0
            db "Cancel",0
menu_len    equ $-menu_def
al_keys:    dw 800Dh,80FBh,0,0
            db "OK",0
t_noslot:   db "FONTDMP5: no free typo slot (0-15): nothing done",0
t_sum1:     db "FONTDMP5 files written=",0
t_skip:     db " skipped(exist)=",0
t_fail:     db " failed=",0
t_miss:     db " no-font=",0
t_sum2:     db "test def=",0
t_init:     db " init=",0
t_src:      db " list=",0
t_last:     db " last file=",0
t_lastfail: db "last failure ",0

; ============================================================================
; variables
; ============================================================================
app_bank:   defs 1
wr_err:     defs 1
env_ink:    defs 1
env_mode:   defs 1
env_slot:   defs 1
env_win_f:  defs 1
env_win:    defs 8
menu_choice: defs 1
sv_e:       defs 1
slot_tab:   defs 16
slot_use:   db 0FFh
all_empty:  defs 1
init_done:  db 0
init_f:     db 0FFh
test_a:     db 0FFh
lst_cur:    defs 2
lst_src:    defs 1
times_ptr:  defs 2
swiss_ptr:  defs 2
sz_ptr:     defs 2
cur_size:   defs 1
cur_face:   defs 1
cur_ch:     defs 1
cur_acc:    defs 1
cf_mx:      defs 1
cf_my:      defs 1
ct_ptr:     defs 2
cf_family:  defs 1
cf_style:   defs 1
cf_styles:  defs 1
cf_entry:   defs 2
cf_def_a:   defs 1
cf_def_f:   defs 1
cf_glyphs:  defs 2
rect_asc:   defs 1
rect_h:     defs 1
rect_flags: defs 1
cr_x:       defs 2
cr_y:       defs 2
cr_rowb:    defs 1
cr_h:       defs 1
cp_dst:     defs 2
cp_px:      defs 2
cp_y:       defs 1
cp_nb:      defs 1
cap_len:    defs 2
dg_rect:    defs 8
n_done:     defs 1
n_skip:     defs 1
n_fail:     defs 1
n_missing:  defs 1
fail_kind:  defs 1
fail_code:  defs 1
stem:       db "FD5TN012",0
last_done:  db "(none)",0,0,0
last_fail:  db "(none)",0,0,0
lr_base:    defs 2
lr_len:     defs 2
lr_src:     defs 2
rec_len:    defs 2
rec_ptr:    defs 2
rec_hdr:    defs 6
hdr_var:    defs 8
tim_buf:    defs 4
face_rec:   defs 43
info_a:     db 0FFh             ; INFO record: A, HL, 8 bytes (contiguous)
info_hl:    defs 2
info_data:  defs 8
gh:         defs GH_LEN
al_text:    defs 160
lst1:       defs LREC
lst2:       defs LREC
buf_w:      defs BUFN
buf_k:      defs BUFN
image_end:
