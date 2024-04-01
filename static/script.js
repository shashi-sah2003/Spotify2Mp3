document.addEventListener("DOMContentLoaded", function(){
    const form = document.getElementById("playlist-form");
    form.addEventListener("submit", function(event){
        event.preventDefault();
        const formData = new FormData(form);
        const playlistLink = formData.get("playlist_link");
        const userid = generateUserId();
        fetch("/download_songs", {
            method: "POST",
            body: new URLSearchParams({ playlist_link: playlistLink, userid: userid }),
            headers:{
                "Content-Type": "application/x-www-form-urlencoded",
            },
        })
        .then(response => response.json())
        .then(data => {
            const userFolder = data.user_folder;
            const songs = data.songs;
            const downloadContainer = document.getElementById("downloads");
            if(downloadContainer){
                songs.forEach(song => {
                    const downloadLink = document.createElement("a");
                    downloadLink.href = `/download/${userid}/${song}`;
                    downloadLink.textContent = `Download ${song}`;
                    downloadContainer.appendChild(downloadLink);
                    downloadContainer.appendChild(document.createElement("br"));
                });
            } else {
                console.error("Download container not found.");
            }
        })
        .catch(error => {
            console.error("Error: ", error);
        });
    });

    function generateUserId(){
        return Math.random().toString(36).substring(2,9);
    }
});
