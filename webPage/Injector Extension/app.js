
function sleep(milliseconds) {
    return new Promise(resolve => setTimeout(resolve, milliseconds));
}

sleep(5000).then(function()
{
    // var vediamo = document.getElementById("refresh");
    // vediamo.click();
    var vediamo = document.getElementById("clickMe");
    vediamo.click();
});

sleep(10000).then(function()
{
    // var vediamo = document.getElementById("refresh");
    // vediamo.click();
    var vediamo = document.getElementById("clickMe");
    vediamo.click();
});

sleep(15000).then(function()
{
    // var vediamo = document.getElementById("refresh");
    // vediamo.click();
    var vediamo = document.getElementById("clickMe");
    vediamo.click();
});
