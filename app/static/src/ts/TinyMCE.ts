import tinymce from 'tinymce';

async function startTinyMCE() {
    tinymce.remove('textarea#custom_html');

    await tinymce.init({
        branding: false,
        promotion: false,
        statusbar: false,
        border_width: 0,
        selector: 'textarea#custom_html',
        plugins: 'preview importcss searchreplace autolink autosave save directionality code visualblocks visualchars fullscreen link media codesample table charmap pagebreak nonbreaking anchor insertdatetime advlist lists wordcount help charmap quickbars emoticons',
        menubar: 'view help',
        toolbar: 'undo redo | bold italic underline strikethrough | fontfamily fontsize blocks | alignleft aligncenter alignright alignjustify | outdent indent |  numlist bullist | forecolor backcolor removeformat | pagebreak | charmap emoticons | fullscreen  preview save | image media template link anchor codesample | ltr rtl',
        toolbar_sticky: false,
        autosave_ask_before_unload: true,
        autosave_interval: '30s',
        autosave_prefix: '{path}{query}-{id}-',
        autosave_restore_when_empty: false,
        autosave_retention: '2m',
        image_advtab: false,
        importcss_append: false,
        quickbars_selection_toolbar: 'bold italic | quicklink h2 h3 blockquote quickimage quicktable',
        noneditable_class: 'mceNonEditable',
        toolbar_mode: 'sliding',
        contextmenu: false,
        content_css: isDarkMode() ? 'dark' : 'default',
        skin_url: '/static/tinymce/' + (isDarkMode() ? 'dark' : 'light'),
        base_url: '/static/node_modules/tinymce',
    });
}

export default startTinyMCE;