int main() {
    int x = 0;
    
    while (x < 10) {
        x++;
    }
    
    for (int i = 0; i < 5; i++) {
        if (i % 2 == 0) {
            continue;
        }
        x += i;
    }
    
    do {
        x--;
    } while (x > 5);
    
    switch (x) {
        case 1:
            x = 10;
            break;
        case 2:
            x = 20;
        case 3:
            x += 5;
            break;
        default:
            x = 0;
    }
    
    return x;
}