/* Original isolated runner. Student sources are never rewritten. */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <fcntl.h>
#include "api.h"

struct test_case {
    int fn;
    const char *id, *label;
    const char *a;
    size_t na;
    const char *b;
    size_t nb;
    const char *want;
    size_t nw, n, m;
    long long k, e;
    int side, fail;
};
#include "cases.h"

static int detail_fd = 2;
static int inject_at, allocation_calls, injected, suppress_injection;
static int use_valgrind;
static size_t block_count;
struct block { void *raw, *ptr; size_t size; int live; };
static struct block blocks[60000];
void *__real_malloc(size_t n);
void __real_free(void *p);

static void fail(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    vdprintf(detail_fd, format, args);
    va_end(args);
    _exit(1);
}

static void equal(long long got, long long expected, const char *what)
{
    if (got != expected)
        fail("%s ; attendu=%lld ; obtenu=%lld", what, expected, got);
}

static void require(int yes, const char *what)
{
    if (!yes)
        fail("%s ; attendu=vrai ; obtenu=faux", what);
}

static void same_bytes(const void *got, const void *expected, size_t size)
{
    const unsigned char *g = got, *e = expected;
    for (size_t i = 0; i < size; i++)
        if (g[i] != e[i])
            fail("octet[%zu] ; attendu=0x%02x ; obtenu=0x%02x", i, e[i], g[i]);
}

static void check_redzones(struct block *b)
{
    if (use_valgrind)
        return;
    unsigned char *raw = b->raw, *end = (unsigned char *)b->ptr + b->size;
    for (int i = 0; i < 32; i++) {
        if (raw[i] != 0xa7)
            fail("écriture avant le bloc alloué ; attendu=zone intacte ; obtenu=zone modifiée");
        if (end[i] != 0xa7)
            fail("écriture après le bloc alloué ; attendu=zone intacte ; obtenu=zone modifiée");
    }
}

void *__wrap_malloc(size_t n)
{
    if (!suppress_injection) {
        allocation_calls++;
        if (inject_at && allocation_calls == inject_at) {
            injected = 1;
            errno = ENOMEM;
            return NULL;
        }
    }
    if (n > 64 * 1024 * 1024 || n > SIZE_MAX - 64) {
        errno = ENOMEM;
        return NULL;
    }
    if (block_count >= sizeof(blocks)/sizeof(*blocks))
        fail("limite interne du suivi des allocations atteinte");
    void *raw = __real_malloc(use_valgrind ? (n ? n : 1) : n + 64);
    if (!raw)
        fail("mémoire insuffisante dans le moteur de test");
    void *p = use_valgrind ? raw : (char *)raw + 32;
    if (!use_valgrind) {
        memset(raw, 0xa7, 32);
        memset((char *)p + n, 0xa7, 32);
    }
    /* Nonzero poison makes incomplete calloc initialization deterministic. */
    if (!use_valgrind)
        memset(p, 0xcc, n);
    blocks[block_count++] = (struct block){raw, p, n, 1};
    return p;
}

void __wrap_free(void *p)
{
    if (!p)
        return;
    for (size_t i = block_count; i > 0; i--) {
        struct block *b = &blocks[i-1];
        if (b->ptr == p) {
            if (!b->live)
                fail("double libération ; attendu=bloc encore vivant ; obtenu=bloc déjà libéré");
            check_redzones(b);
            b->live = 0;
            if (use_valgrind)
                __real_free(b->raw);
            return;
        }
    }
    fail("free sur un pointeur non alloué ou décalé ; attendu=base d'un bloc vivant ; obtenu=%p",p);
}

static void *owned(size_t n)
{
    suppress_injection++;
    void *p = __wrap_malloc(n);
    suppress_injection--;
    return p;
}

static void allocated(void *p, size_t minimum)
{
    require(p != NULL, "allocation réussie hors injection");
    for (size_t i = block_count; i > 0; i--)
        if (blocks[i-1].ptr == p && blocks[i-1].live) {
            if (blocks[i-1].size < minimum)
                fail("taille allouée ; attendu=au moins %zu ; obtenu=%zu",
                     minimum, blocks[i-1].size);
            return;
        }
    fail("résultat ; attendu=bloc alloué indépendant ; obtenu=pointeur non possédé");
}

static void no_leaks(void)
{
    size_t count = 0, bytes = 0;
    for (size_t i = 0; i < block_count; i++) {
        check_redzones(&blocks[i]);
        if (blocks[i].live) {
            count++;
            bytes += blocks[i].size;
        }
    }
    if (count)
        fail("fuite mémoire ; attendu=0 bloc ; obtenu=%zu bloc(s), %zu octet(s)",count,bytes);
    for (size_t i = 0; i < block_count; i++)
        if (!use_valgrind)
            __real_free(blocks[i].raw);
    block_count = 0;
}

/* The byte range abuts a protected page; both leading and trailing layouts
 * are exercised. Const input pages catch accidental writes as well. */
static void *guarded(const void *data, size_t size, int readonly, int side)
{
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    size_t span = ((size ? size : 1) + page - 1) / page * page;
    char *base = mmap(NULL, span + 2 * page, PROT_NONE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (base == MAP_FAILED || mprotect(base+page, span, PROT_READ|PROT_WRITE))
        fail("moteur : impossible de créer les pages de garde");
    char *p = side ? base+page : base+page+span-size;
    if (size)
        memcpy(p, data, size);
    if (readonly && mprotect(base+page,span,PROT_READ))
        fail("moteur : impossible de protéger une entrée constante");
    return p;
}

static int signum(int x) { return (x > 0) - (x < 0); }

static void pointer_result(const void *p, const void *base, long long offset)
{
    const void *expected = offset < 0 ? NULL : (const char *)base + offset;
    if (p != expected)
        fail("pointeur retourné ; attendu=%s, offset=%lld ; obtenu=%s, adresse=%p",
             expected ? "entrée" : "NULL", offset, p ? "non NULL" : "NULL", p);
}

static int callback_kind;
static unsigned int callback_count;
static char *callback_base;
static char transform(unsigned int i, char c)
{
    equal(i, callback_count++, "index du callback");
    if (callback_kind == 1)
        return 0;
    return callback_kind == 2 ? c : (char)((unsigned char)c + i);
}
static void transform_inplace(unsigned int i, char *p)
{
    require(p == callback_base+i, "adresse transmise au callback");
    *p = transform(i, *p);
}

static unsigned int list_calls, del_calls;
static int list_kind;
struct box { int *value; };
static void *map_content(void *p)
{
    /* Callback allocations are NOT student allocation failures. A NULL
     * callback result is a valid content value, not necessarily an error. */
    list_calls++;
    if (list_kind == 1)
        return p;
    if (list_kind == 2)
        return NULL;
    struct box *b = owned(sizeof(*b));
    b->value = owned(sizeof(int));
    *b->value = *(int *)p + 17;
    return b;
}
static void delete_box(void *p)
{
    del_calls++;
    if (list_kind != 0)
        return;
    struct box *b = p;
    __wrap_free(b->value);
    __wrap_free(b);
}
static int *list_values;
static unsigned char list_seen[12000];
static void observe_content(void *p)
{
    uintptr_t address = (uintptr_t)p, first = (uintptr_t)list_values;
    require(address >= first && address < first+12000*sizeof(int) &&
            (address-first)%sizeof(int)==0, "del reçoit le contenu du nœud");
    size_t i = (address-first)/sizeof(int);
    equal(list_seen[i]++,0,"contenu transmis une seule fois à del");
    del_calls++;
}
static void visit_content(void *p)
{
    require(p == &list_values[list_calls], "ordre et adresse des contenus");
    (*(int *)p) += 17;
    list_calls++;
}

static void free_nodes(t_list *p, int with_content)
{
    size_t bound = 0;
    while (p) {
        require(bound++ < 12000,"liste finie, sans cycle");
        t_list *next = p->next;
        if (with_content)
            delete_box(p->content);
        __wrap_free(p);
        p = next;
    }
}

static void list_test(const struct test_case *c)
{
    t_list *nodes[10002], *head = NULL, *result;
    int values[12000];
    list_values=values;
    memset(list_seen,0,sizeof(list_seen));
    list_calls=del_calls=0;
    list_kind=(int)c->k;
    if (c->fn==F_lstnew) {
        void *content = c->n ? &values[0] : NULL;
        result=ft_lstnew(content);
        if (injected) { require(result==NULL,"NULL après échec de malloc"); return; }
        allocated(result,sizeof(*result));
        require(result->content==content,"content conserve le pointeur reçu");
        require(result->next==NULL,"next initialisé à NULL");
        __wrap_free(result);
        return;
    }
    for (size_t i=0;i<c->n;i++) {
        nodes[i]=owned(sizeof(t_list));
        values[i]=(int)i;
        nodes[i]->content=&values[i];
        nodes[i]->next=NULL;
        if (i) nodes[i-1]->next=nodes[i];
        else head=nodes[i];
    }
    switch(c->fn) {
    case F_lstsize:
        equal(ft_lstsize(head),c->n,"nombre de nœuds");
        break;
    case F_lstlast:
        require(ft_lstlast(head)==(c->n?nodes[c->n-1]:NULL),"dernier nœud ou NULL");
        break;
    case F_lstadd_front:
    case F_lstadd_back: {
        t_list *extra=owned(sizeof(t_list)), *tail=owned(sizeof(t_list));
        extra->content=&values[c->n]; extra->next=tail;
        tail->content=&values[c->n+1]; tail->next=NULL;
        if(c->fn==F_lstadd_front) {
            ft_lstadd_front(&head,extra);
            require(head==extra,"nouvelle tête");
            require(extra->next==(c->n?nodes[0]:NULL),"lien vers ancienne tête");
            __wrap_free(extra); __wrap_free(tail);
        } else {
            ft_lstadd_back(&head,extra);
            require(head==(c->n?nodes[0]:extra),"tête conservée");
            require((c->n?nodes[c->n-1]->next:head)==extra,"ajout en fin");
            require(extra->next==tail && tail->next==NULL,"chaîne ajoutée conservée");
            if(c->n) nodes[c->n-1]->next=NULL;
            __wrap_free(extra); __wrap_free(tail);
        }
        head=c->n?nodes[0]:NULL;
        break;
    }
    case F_lstdelone:
        ft_lstdelone(head,observe_content);
        equal(del_calls,1,"un appel à del");
        equal(list_seen[0],1,"del reçoit le contenu exact");
        /* The next node must remain alive; reading it also detects a bad free. */
        for(size_t i=1;i<c->n;i++) {
            allocated(nodes[i],sizeof(t_list));
            require(nodes[i]->content==&values[i],"successeur conservé");
            __wrap_free(nodes[i]);
        }
        return;
    case F_lstclear:
        if(c->k==1) {
            ft_lstclear(&head->next,observe_content);
            require(head==nodes[0] && head->next==NULL,"préfixe conservé et lien remis à NULL");
            equal(del_calls,c->n-1,"del appelé seulement sur le suffixe");
            equal(list_seen[0],0,"contenu du préfixe conservé");
            for(size_t i=1;i<c->n;i++) equal(list_seen[i],1,"contenu du suffixe détruit");
            __wrap_free(head); return;
        }
        ft_lstclear(&head,observe_content);
        require(head==NULL,"tête remise à NULL");
        equal(del_calls,c->n,"del appelé pour chaque contenu");
        for(size_t i=0;i<c->n;i++) equal(list_seen[i],1,"contenu libéré via del");
        return;
    case F_lstiter:
        ft_lstiter(head,visit_content);
        equal(list_calls,c->n,"nombre d'appels au callback");
        for(size_t i=0;i<c->n;i++) equal(values[i],i+17,"contenu modifié par callback");
        break;
    case F_lstmap: {
        result=ft_lstmap(head,map_content,delete_box);
        if(injected) {
            require(result==NULL,"NULL après échec d'allocation d'un nœud");
            equal(del_calls,list_calls,"chaque contenu créé est détruit par del");
        } else {
            equal(list_calls,c->n,"callback une fois par nœud");
            equal(del_calls,0,"aucun del sur réussite");
            t_list *p=result;
            for(size_t i=0;i<c->n;i++) {
                allocated(p,sizeof(t_list));
                for(size_t j=0;j<c->n;j++) require(p!=nodes[j],"nœud résultat indépendant");
                if(list_kind==0) {
                    struct box *b=p->content;
                    allocated(b,sizeof(*b)); allocated(b->value,sizeof(int));
                    equal(*b->value,i+17,"contenu transformé");
                } else require(p->content==(list_kind==1?(void *)&values[i]:NULL),"valeur du callback conservée");
                p=p->next;
            }
            require(p==NULL,"liste résultat terminée");
            free_nodes(result,1);
        }
        break;
    }
    default: fail("moteur : fonction liste inconnue");
    }
    for(size_t i=0;i<c->n;i++) {
        require(nodes[i]->content==&values[i],"pointeur content original conservé");
        require(nodes[i]->next==(i+1<c->n?nodes[i+1]:NULL),"liens originaux conservés");
    }
    free_nodes(head,0);
}

static void test_body(const struct test_case *c)
{
    void *p;
    char *a=NULL, *b=NULL;
    long long value=0;
    if(c->fn>=F_lstnew) { list_test(c); return; }
    int writable=c->fn==F_memset || c->fn==F_bzero || c->fn==F_memcpy ||
        c->fn==F_memmove || c->fn==F_strlcpy || c->fn==F_strlcat || c->fn==F_striteri;
    a=guarded(c->a,c->na,!writable,c->side);
    b=guarded(c->b,c->nb,1,c->side);
    switch(c->fn) {
    case F_isalpha: equal(ft_isalpha(c->k),c->e,"retour exact 0 ou 1"); return;
    case F_isdigit: equal(ft_isdigit(c->k),c->e,"retour exact 0 ou 1"); return;
    case F_isalnum: equal(ft_isalnum(c->k),c->e,"retour exact 0 ou 1"); return;
    case F_isascii: equal(ft_isascii(c->k),c->e,"retour exact 0 ou 1"); return;
    case F_isprint: equal(ft_isprint(c->k),c->e,"retour exact 0 ou 1"); return;
    case F_toupper: equal(ft_toupper(c->k),c->e,"caractère retourné"); return;
    case F_tolower: equal(ft_tolower(c->k),c->e,"caractère retourné"); return;
    case F_strlen: equal(ft_strlen(a),c->e,"longueur en octets"); return;
    case F_atoi: equal(ft_atoi(a),c->e,"entier décimal"); return;
    case F_strchr: pointer_result(ft_strchr(a,c->k),a,c->e); return;
    case F_strrchr: pointer_result(ft_strrchr(a,c->k),a,c->e); return;
    case F_memchr: pointer_result(ft_memchr(a,c->k,c->n),a,c->e); return;
    case F_strnstr: pointer_result(ft_strnstr(a,b,c->n),a,c->e); return;
    case F_strncmp: equal(signum(ft_strncmp(a,b,c->n)),c->e,"signe du résultat"); return;
    case F_memcmp: equal(signum(ft_memcmp(a,b,c->n)),c->e,"signe du résultat"); return;
    case F_memset: require(ft_memset(a+c->m,c->k,c->n)==a+c->m,"retour destination"); break;
    case F_bzero: ft_bzero(a+c->m,c->n); break;
    case F_memcpy: require(ft_memcpy(a+c->m,b,c->n)==a+c->m,"retour destination"); break;
    case F_memmove: require(ft_memmove(a+c->k,a+c->m,c->n)==a+c->k,"retour destination"); break;
    case F_strlcpy: equal(ft_strlcpy(a,b,c->n),c->e,"longueur totale source"); break;
    case F_strlcat: equal(ft_strlcat(a,b,c->n),c->e,"longueur totale tentée"); break;
    case F_striteri:
        callback_kind=c->k; callback_count=0; callback_base=a;
        ft_striteri(a,transform_inplace);
        equal(callback_count,c->na-1,"callback pour chaque caractère, sans le NUL");
        break;
    case F_calloc:
        p=ft_calloc(c->n,c->m);
        if(injected || c->e) { require(p==NULL,"NULL sur échec ou multiplication débordante"); return; }
        allocated(p,c->n*c->m);
        for(size_t i=0;i<c->n*c->m;i++) equal(((unsigned char *)p)[i],0,"calloc initialisé à zéro");
        if(c->n*c->m==0) {
            void *q=ft_calloc(c->n,c->m);
            if(injected) require(q==NULL,"NULL après échec de malloc");
            else { allocated(q,0); require(q!=p,"deux allocations zéro distinctes"); __wrap_free(q); }
        }
        __wrap_free(p); return;
    case F_strdup: p=ft_strdup(a); goto allocated_string;
    case F_substr: p=ft_substr(a,(unsigned int)c->m,c->n); goto allocated_string;
    case F_strjoin: p=ft_strjoin(a,b); goto allocated_string;
    case F_strtrim: p=ft_strtrim(a,b); goto allocated_string;
    case F_itoa: p=ft_itoa(c->k); goto allocated_string;
    case F_strmapi:
        callback_kind=c->k; callback_count=0;
        p=ft_strmapi(a,transform);
        if(!injected) equal(callback_count,c->na-1,"nombre d'appels au callback");
        goto allocated_string;
    case F_split: {
        char **parts=ft_split(a,(char)c->k);
        if(injected) { require(parts==NULL,"NULL après échec d'une allocation"); return; }
        allocated(parts,(c->e+1)*sizeof(char *));
        const char *w=(const char *)c->want;
        for(long long i=0;i<c->e;i++) {
            size_t len=strlen(w)+1;
            allocated(parts[i],len);
            same_bytes(parts[i],w,len);
            for(long long j=0;j<i;j++) require(parts[i]!=parts[j],"mots alloués indépendamment");
            w+=len;
        }
        require(parts[c->e]==NULL,"tableau terminé par NULL");
        for(long long i=0;i<c->e;i++) __wrap_free(parts[i]);
        __wrap_free(parts); return;
    }
    case F_putchar_fd: case F_putstr_fd: case F_putendl_fd: case F_putnbr_fd: {
        FILE *stream=tmpfile();
        if(!stream) fail("moteur : tmpfile indisponible");
        int fd=fileno(stream);
        if(c->m && (int)c->m!=fd) {
            require(dup2(fd,(int)c->m)==(int)c->m,"préparation du descripteur cible");
            fclose(stream); stream=NULL; fd=(int)c->m;
        }
        for(int repeat=0;repeat<(c->e?c->e:1);repeat++) {
            if(c->fn==F_putchar_fd) ft_putchar_fd(c->k,fd);
            if(c->fn==F_putstr_fd) ft_putstr_fd(a,fd);
            if(c->fn==F_putendl_fd) ft_putendl_fd(a,fd);
            if(c->fn==F_putnbr_fd) ft_putnbr_fd(c->k,fd);
        }
        off_t length=lseek(fd,0,SEEK_END);
        equal(length,c->nw,"nombre d'octets écrits sur le fd demandé");
        require(lseek(fd,0,SEEK_SET)==0,"relecture de la sortie");
        unsigned char buffer[4096]; size_t pos=0;
        while(pos<c->nw) {
            ssize_t n=read(fd,buffer,sizeof(buffer));
            require(n>0,"sortie lisible");
            same_bytes(buffer,c->want+pos,(size_t)n); pos+=(size_t)n;
        }
        if(stream) fclose(stream); else close(fd);
        return;
    }
    default: fail("moteur : fonction inconnue (%lld)",value);
    }
    same_bytes(a,c->want,c->nw);
    return;
allocated_string:
    if(injected) { require(p==NULL,"NULL après échec de malloc"); return; }
    allocated(p,c->nw);
    same_bytes(p,c->want,c->nw);
    __wrap_free(p);
}

int main(int argc, char **argv)
{
    if(argc<2) return 2;
    use_valgrind=getenv("ULTIMATE_VALGRIND")!=NULL;
    struct rlimit core={0,0}; setrlimit(RLIMIT_CORE,&core);
    int timeout=argc>2?atoi(argv[2]):2;
    for(size_t i=0;i<sizeof(cases)/sizeof(*cases);i++) {
        const struct test_case *c=&cases[i];
        if(strcmp(argv[1],"all") && strcmp(argv[1],names[c->fn])) continue;
        if(!available(c->fn)) { printf("%s\tMISSING\tfonction absente de libft.a\n",c->id); continue; }
        int channel[2];
        if(pipe(channel)) return 2;
        fflush(NULL);
        pid_t pid=fork();
        if(pid<0) return 2;
        if(pid==0) {
            close(channel[0]); detail_fd=channel[1];
            int sink=open("/dev/null",O_WRONLY);
            if(sink>=0) { dup2(sink,1); dup2(sink,2); close(sink); }
            alarm((unsigned)timeout);
            allocation_calls=0;
            test_body(c);
            int total=allocation_calls;
            if(!may_allocate(c->fn)) equal(total,0,"malloc non autorisé pour cette fonction");
            no_leaks();
            if(c->fail) {
                require(total>0,"au moins une allocation observée pour injecter l'échec");
                for(int j=1;j<=total;j++) {
                    inject_at=j; allocation_calls=0; injected=0;
                    test_body(c);
                    require(injected,"échec malloc effectivement injecté");
                    no_leaks();
                }
            }
            dprintf(detail_fd,"COMPLETED");
            _exit(0);
        }
        close(channel[1]);
        char message[2048]={0}; size_t used=0;
        while(used<sizeof(message)-1) {
            ssize_t n=read(channel[0],message+used,sizeof(message)-1-used);
            if(n<0 && errno==EINTR) continue;
            if(n<=0) break;
            used+=(size_t)n;
        }
        close(channel[0]);
        int status;
        while(waitpid(pid,&status,0)<0) if(errno!=EINTR) return 2;
        const char *state="OK";
        if(WIFSIGNALED(status)) {
            state=WTERMSIG(status)==SIGALRM?"TIMEOUT":"CRASH";
            snprintf(message,sizeof(message),"%s ; attendu=terminaison normale ; obtenu=signal %d",
                     WTERMSIG(status)==SIGALRM?"délai dépassé":"accès mémoire invalide ou interruption",WTERMSIG(status));
        } else if(!WIFEXITED(status) || WEXITSTATUS(status)) state="FAIL";
        else if(strcmp(message,"COMPLETED")) {
            state="FAIL";
            snprintf(message,sizeof(message),"arrêt prématuré ; attendu=fin des vérifications ; obtenu=sortie avant la fin du test");
        } else message[0]=0;
        for(size_t j=0;message[j];j++) if(message[j]=='\n' || message[j]=='\t' || message[j]=='\r') message[j]=' ';
        printf("%s\t%s\t@PID:%ld@%s\n",c->id,state,(long)pid,message); fflush(stdout);
    }
    return 0;
}
