#!/usr/bin/perl
#

select(STDOUT); $|=1;

use Getopt::Std;
getopts('d', \%opts);
$dbg = $opts{"d"};

use IO::Socket;
use Net::hostent;              
use IPC::Open2;

sub usage {
    die "ARGS: -[d] port cmd args*\n";
}

usage() if ($#ARGV < 1);

$Port = shift @ARGV;
$Cmd  = shift @ARGV;
$Args = "@ARGV";
$ServerSocket  =  "";
$ProcPid = "";


# ---------------------------------------------------------
# 			Run code
# ---------------------------------------------------------

subprocessStart();
myTrace("subprocessStart: pid $ProcPid\n");

myTrace("Trying to listen on Port $Port...");
$ServerSocket = IO::Socket::INET->new(Proto     => 'tcp',
				      LocalPort => $Port,
				      Listen    => SOMAXCONN,
				      Reuse     => 1)
    or die "cannot listen on $Port\n";
myTrace("Server listening");


while(1) {
    myTrace("\nBefore accept ...");
    $clientSocket = $ServerSocket->accept();
    $hostInfo = gethostbyaddr($clientSocket->peeraddr); 
    $clientHost = $hostInfo -> name;
    myTrace("Accepted connection from |$clientHost|\n");
    $clientSocket->autoflush(1);


    while($input=<$clientSocket>) {
	myTrace("from client |$input|");
	$answer = subprocessSendReceive($input);
	sendMsg($clientSocket, $answer);
	myTrace("sent to client |$answer|");
    }

    close($clientSocket);
    myTrace("** End of connection with client **");

}

subprocessKill();


# -------------------------------------------------------
# 	SUBROUTINES
# -------------------------------------------------------


sub subprocessStart {
    $ProcPid = open2 (*SUB_IN, *SUB_OUT, "$Cmd $Args 2>/dev/null");
    select(SUB_OUT); $|=1;
}

sub subprocessKill {
    kill 9, $ProcPid;
}

sub subprocessSendReceive {
    my($send_line) = @_;

    print SUB_OUT $send_line;
    myTrace("\n  **-> $send_line");

    my($rec_line);
    $rec_line = <SUB_IN>;
    myTrace("  **<- $rec_line");
    return $rec_line;
}

sub myTrace {
    print STDERR $_[0]."\n" if($dbg);
}

sub sendMsg {
    my ($socket, $txt) = @_;
    # $txt .= "\n";
    print $socket $txt;
}

sub chopMsg {
    my ($msgRef) = @_;
    $$msgRef =~ s/[\r\n]+$//;
}
